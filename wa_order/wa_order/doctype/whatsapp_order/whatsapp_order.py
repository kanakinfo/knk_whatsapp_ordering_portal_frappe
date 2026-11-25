"""The review queue document.

Lives inside ERPNext so the whole flow - message, parse, correct, post - is
visible in one system. Correcting a line here re-prices and re-converts it
from live master data rather than trusting whatever the agent sent.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, nowdate

from wa_order.utils import get_item_rate, get_settings, resolve_uom

BLOCKING_CODES_CLEARED_BY_CORRECTION = {
    "no_match",
    "low_confidence_match",
    "ambiguous_pack_size",
    "ambiguous_match",
    "unknown_uom",
}

CUSTOMER_CODES = {"no_customer", "weak_customer_match", "customer_conflict"}

EDITABLE_STATUSES = {"Pending", "Needs Review", "Failed"}


class WhatsAppOrder(Document):
    # ------------------------------------------------------------ lifecycle
    def validate(self):
        self.recalculate_lines()
        self.calculate_total()
        self.clear_resolved_issues()

    def _previous_lines(self):
        """Child rows as they were before this save, keyed by row name.

        get_doc_before_save() only exists on the parent - calling it on a child
        row always returns None, which would make every line look "changed" and
        silently overwrite an operator's manual quantity edit on every save.
        """
        before = self.get_doc_before_save()
        if not before:
            return {}
        return {row.name: row for row in (before.items or []) if row.name}

    def recalculate_lines(self):
        """Re-price and re-convert any line whose item was changed.

        The operator picks an item; everything else is derived here so a
        correction cannot post a stale rate or the previous item's case factor.
        A line whose item did NOT change keeps whatever qty the operator typed.
        """
        settings = get_settings()
        previous_lines = self._previous_lines()

        for idx, line in enumerate(self.items, start=1):
            line.idx = idx
            if not line.item_code:
                line.qty = 0
                line.amount = 0
                continue

            item = frappe.db.get_value(
                "Item", line.item_code, ["stock_uom", "item_name"], as_dict=True
            )
            if not item:
                frappe.throw(_("Row {0}: Item {1} does not exist.").format(
                    idx, line.item_code))

            previous = previous_lines.get(line.name)
            item_changed = bool(
                previous is None
                or getattr(previous, "item_code", None) != line.item_code
            )

            # Recompute from the asked quantity whenever the item changed, so
            # switching a 100g SKU to the 250g one re-applies the right factor.
            if item_changed and line.requested_qty:
                qty, uom, factor, note = resolve_uom(
                    line.item_code, item.stock_uom,
                    line.requested_uom, line.requested_qty,
                )
                line.qty = qty
                line.uom = uom
                line.conversion_factor = factor
                if note:
                    line.match_note = note

            if not line.uom:
                line.uom = item.stock_uom
            if not line.conversion_factor:
                line.conversion_factor = 1.0

            if item_changed or not line.rate:
                line.rate = get_item_rate(
                    line.item_code, settings.selling_price_list,
                    uom=line.uom, customer=self.customer,
                )

            line.currency = self.currency
            line.amount = flt(line.qty) * flt(line.rate)

    def calculate_total(self):
        self.total = sum(flt(line.amount) for line in self.items)

    def clear_resolved_issues(self):
        """Drop issues the operator has fixed, so the form reflects reality."""
        if self.is_new():
            return
        keep = []
        for issue in self.issues:
            code = issue.code or ""
            if code in CUSTOMER_CODES and self.customer:
                continue
            if code in BLOCKING_CODES_CLEARED_BY_CORRECTION:
                line = self._line_at(issue.line_no)
                if line is None or line.item_code:
                    continue
            keep.append(issue)
        if len(keep) != len(self.issues):
            self.issues = keep
            for idx, issue in enumerate(self.issues, start=1):
                issue.idx = idx

    def _line_at(self, line_no):
        if not line_no:
            return None
        for line in self.items:
            if line.idx == line_no:
                return line
        return None

    # ------------------------------------------------------------- helpers
    @property
    def blockers(self):
        return [i for i in self.issues if i.severity == "Blocker"]

    def ready_to_post(self):
        """What still stands between this order and a Sales Order."""
        reasons = []
        if not self.customer:
            reasons.append(_("No customer is set."))
        postable = [l for l in self.items if l.item_code and flt(l.qty) > 0]
        if not postable:
            reasons.append(_("No line has both an item and a quantity."))
        return reasons

    # -------------------------------------------------------------- actions
    @frappe.whitelist()
    def approve(self, ignore_blockers=False):
        """Create the Sales Order. Unresolved lines are dropped, not guessed."""
        if self.status in ("Approved", "Auto Posted") and self.sales_order:
            frappe.throw(_("Already posted as {0}.").format(self.sales_order))

        reasons = self.ready_to_post()
        if reasons:
            frappe.throw("<br>".join(reasons))

        blockers = self.blockers
        if blockers and not frappe.parse_json(str(ignore_blockers).lower() or "false"):
            msg = "<br>".join(f"&bull; {b.message}" for b in blockers)
            frappe.throw(
                _("This order has unresolved blockers:<br>{0}<br><br>"
                  "Fix them, or use <b>Approve Anyway</b> to override.").format(msg),
                title=_("Blocked"),
            )

        try:
            sales_order = self.make_sales_order()
        except Exception as exc:
            self.db_set("status", "Failed")
            self.db_set("error_message", str(exc)[:500])
            frappe.log_error(frappe.get_traceback(),
                             f"WhatsApp Order {self.name} posting failed")
            raise

        self.db_set("sales_order", sales_order.name)
        self.db_set("status", "Approved")
        self.db_set("error_message", None)

        frappe.msgprint(
            _("Sales Order {0} created.").format(
                frappe.utils.get_link_to_form("Sales Order", sales_order.name)),
            alert=True, indicator="green",
        )
        self.notify_sender()
        return sales_order.name

    def make_sales_order(self):
        settings = get_settings()
        delivery_date = add_days(nowdate(), int(settings.delivery_lead_days or 2))

        so = frappe.new_doc("Sales Order")
        so.customer = self.customer
        so.company = settings.company
        so.transaction_date = nowdate()
        so.delivery_date = delivery_date
        so.currency = self.currency or frappe.get_cached_value(
            "Company", settings.company, "default_currency")
        so.selling_price_list = settings.selling_price_list
        so.order_type = "Sales"
        # Traceability both ways: po_no is visible on print, wa_order_ref links back.
        so.po_no = self.name
        so.wa_order_ref = self.name

        for line in self.items:
            if not line.item_code or flt(line.qty) <= 0:
                continue
            so.append("items", {
                "item_code": line.item_code,
                "qty": flt(line.qty),
                "uom": line.uom,
                "rate": flt(line.rate),
                "warehouse": settings.warehouse,
                "delivery_date": delivery_date,
                "description": line.raw_text or line.item_text,
            })

        so.flags.ignore_permissions = True
        so.insert()
        if settings.submit_sales_order:
            so.submit()
        return so

    def make_sales_order_and_mark(self):
        """Used by the auto-post path in api.ingest()."""
        sales_order = self.make_sales_order()
        self.db_set("sales_order", sales_order.name)
        self.db_set("status", "Auto Posted")
        self.db_set("error_message", None)
        return sales_order.name

    @frappe.whitelist()
    def reject(self, reason=None):
        if self.sales_order:
            frappe.throw(_("Cannot reject: already posted as {0}.").format(
                self.sales_order))
        self.db_set("status", "Rejected")
        if reason:
            self.db_set("error_message", f"Rejected: {reason}")
        frappe.msgprint(_("Order rejected."), alert=True, indicator="orange")
        return True

    def notify_sender(self):
        """Ask the agent service to send the confirmation reply.

        Best effort: a reply that fails must never roll back a posted order.
        """
        settings = get_settings()
        if not settings.notify_on_approve or not settings.agent_url:
            return
        try:
            import requests

            token = settings.get_password("agent_token", raise_exception=False)
            requests.post(
                settings.agent_url.rstrip("/") + "/api/notify",
                json={
                    "whatsapp_order": self.name,
                    "to": self.sender_phone,
                    "sales_order": self.sales_order,
                    "total": flt(self.total),
                    "currency": self.currency,
                    "lines": [
                        {
                            "item_name": l.item_name,
                            "qty": flt(l.qty),
                            "uom": l.uom,
                            "amount": flt(l.amount),
                        }
                        for l in self.items if l.item_code
                    ],
                },
                headers={"X-Agent-Token": token or ""},
                timeout=10,
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"WhatsApp reply failed for {self.name}")


@frappe.whitelist()
def approve_order(name, ignore_blockers=False):
    doc = frappe.get_doc("WhatsApp Order", name)
    doc.check_permission("write")
    return doc.approve(ignore_blockers=ignore_blockers)


@frappe.whitelist()
def reject_order(name, reason=None):
    doc = frappe.get_doc("WhatsApp Order", name)
    doc.check_permission("write")
    return doc.reject(reason=reason)
