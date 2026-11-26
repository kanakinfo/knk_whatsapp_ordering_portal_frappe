"""Whitelisted endpoints the order agent calls.

Two of them matter:

  catalogue()  one call returning items, dealer aliases, UOM conversions,
               prices, stock and customers. The agent used to need five REST
               round-trips for this; on a 5,000-SKU master that was the
               slowest part of the loop.

  ingest()     the agent posts a parsed order; ERPNext decides whether it is
               confident enough to post, and creates the Sales Order itself.
               The decision lives here, not in the agent, so changing a
               threshold in Settings changes behaviour with no redeploy.
"""
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime, nowdate

from knk_whatsapp_ordering_portal_frappe.utils import (
    get_item_rate,
    get_settings,
    normalise_phone,
    resolve_uom,
)


def has_app_permission():
    """Who sees the WhatsApp Orders icon on the v16 apps screen.

    v16 requires has_permission hooks to return True explicitly; a truthy
    value is no longer enough.
    """
    roles = set(frappe.get_roles())
    allowed = {"Sales User", "Sales Manager", "System Manager", "Administrator"}
    return True if roles & allowed else False


# --------------------------------------------------------------- catalogue

@frappe.whitelist()
def catalogue(include_stock=True, item_group=None, limit=None):
    """Everything the matcher needs about sellable items and customers."""
    frappe.only_for(("Sales User", "Sales Manager", "System Manager"))
    settings = get_settings()

    filters = {"disabled": 0, "is_sales_item": 1}
    if item_group:
        filters["item_group"] = item_group

    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=["name as item_code", "item_name", "stock_uom", "brand",
                "item_group", "description"],
        limit_page_length=cint(limit) or 0,
        order_by="item_name",
    )
    if not items:
        return {"items": [], "customers": [], "settings": _settings_payload(settings)}

    codes = [i.item_code for i in items]
    aliases = _aliases_by_item(codes)
    conversions = _conversions_by_item(codes)
    prices = _prices_by_item(codes, settings.selling_price_list)
    stock = _stock_by_item(codes, settings.warehouse) if frappe.parse_json(
        str(include_stock).lower()) else {}
    excluded = set(frappe.get_all(
        "Item", filters={"name": ["in", codes], "wa_exclude": 1},
        pluck="name") or [])

    payload = []
    for item in items:
        if item.item_code in excluded:
            continue
        payload.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "stock_uom": item.stock_uom,
            "brand": item.brand,
            "item_group": item.item_group,
            "rate": prices.get(item.item_code, 0.0),
            "actual_qty": stock.get(item.item_code, 0.0),
            "aliases": aliases.get(item.item_code, []),
            "uom_conversions": conversions.get(item.item_code, {}),
        })

    return {
        "items": payload,
        "customers": _customers(),
        "settings": _settings_payload(settings),
    }


def _settings_payload(settings):
    return {
        "company": settings.company,
        "price_list": settings.selling_price_list,
        "warehouse": settings.warehouse,
        "currency": frappe.get_cached_value(
            "Company", settings.company, "default_currency") if settings.company else "INR",
        "autopost_confidence": flt(settings.autopost_confidence) or 0.82,
        "match_accept_threshold": flt(settings.match_accept_threshold) or 0.72,
        "enforce_credit_limit": bool(settings.enforce_credit_limit),
        "enforce_stock": bool(settings.enforce_stock),
    }


def _aliases_by_item(codes):
    rows = frappe.get_all(
        "Item Dealer Alias",
        filters={"parent": ["in", codes], "parenttype": "Item"},
        fields=["parent", "alias"],
    )
    out = {}
    for r in rows:
        if r.alias:
            out.setdefault(r.parent, []).append(r.alias.strip())
    return out


def _conversions_by_item(codes):
    rows = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": ["in", codes], "parenttype": "Item"},
        fields=["parent", "uom", "conversion_factor"],
    )
    out = {}
    for r in rows:
        if r.uom and flt(r.conversion_factor) > 0:
            out.setdefault(r.parent, {})[r.uom.strip().lower()] = flt(r.conversion_factor)
    return out


def _prices_by_item(codes, price_list):
    if not price_list:
        return {}
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", codes], "price_list": price_list, "selling": 1},
        fields=["item_code", "price_list_rate", "customer", "uom"],
        order_by="modified desc",
    )
    out = {}
    for r in rows:
        # Plain list price wins for the catalogue; customer-specific pricing is
        # applied per order at posting time.
        if r.customer:
            continue
        out.setdefault(r.item_code, flt(r.price_list_rate))
    return out


def _stock_by_item(codes, warehouse):
    filters = {"item_code": ["in", codes]}
    if warehouse:
        filters["warehouse"] = warehouse
    rows = frappe.get_all("Bin", filters=filters,
                          fields=["item_code", "actual_qty"])
    out = {}
    for r in rows:
        out[r.item_code] = out.get(r.item_code, 0.0) + flt(r.actual_qty)
    return out


def _customers():
    rows = frappe.get_all(
        "Customer",
        filters={"disabled": 0},
        fields=["name", "customer_name", "mobile_no", "territory",
                "default_price_list", "wa_additional_numbers", "wa_aliases"],
    )
    limits = {}
    for r in frappe.get_all("Customer Credit Limit",
                            fields=["parent", "credit_limit"]):
        limits[r.parent] = flt(r.credit_limit)

    out = []
    for c in rows:
        phones = []
        primary = normalise_phone(c.mobile_no)
        if primary:
            phones.append(primary)
        for extra in (c.wa_additional_numbers or "").splitlines():
            n = normalise_phone(extra)
            if n and n not in phones:
                phones.append(n)
        aliases = [a.strip() for a in (c.wa_aliases or "").splitlines() if a.strip()]
        out.append({
            "name": c.name,
            "customer_name": c.customer_name,
            "phones": phones,
            "aliases": aliases,
            "territory": c.territory,
            "credit_limit": limits.get(c.name, 0.0),
            "outstanding": get_outstanding(c.name),
        })
    return out


def get_outstanding(customer):
    """Open receivable for a customer. Falls back if ERPNext's helper moves."""
    try:
        from erpnext.selling.doctype.customer.customer import get_customer_outstanding

        settings = get_settings()
        return flt(get_customer_outstanding(customer, settings.company))
    except Exception:
        total = frappe.db.sql(
            """SELECT COALESCE(SUM(outstanding_amount), 0)
               FROM `tabSales Invoice`
               WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0""",
            customer,
        )
        return flt(total[0][0]) if total else 0.0


# ------------------------------------------------------------------ ingest

@frappe.whitelist(methods=["POST"])
def ingest(payload=None):
    """Create a WhatsApp Order from the agent's parsed message.

    Expected payload (JSON):
      message_id, sender_phone, sender_name, original_message,
      customer, customer_confidence, delivery_note, extraction_method,
      lines: [{raw_text, item_text, item_code, requested_qty, requested_uom,
               confidence, match_note, alternatives}],
      issues: [{severity, code, message, line_no}]

    Returns {name, status, sales_order, total, lines, blockers}.
    """
    frappe.only_for(("Sales User", "Sales Manager", "System Manager"))
    data = _as_dict(payload if payload is not None else frappe.request.data)

    message_id = (data.get("message_id") or "").strip()
    if not message_id:
        frappe.throw(_("message_id is required."))
    if not data.get("sender_phone"):
        frappe.throw(_("sender_phone is required."))

    # WhatsApp retries webhooks. Without this, one message becomes two orders.
    existing = frappe.db.get_value(
        "WhatsApp Order", {"message_id": message_id},
        ["name", "status", "sales_order", "total"], as_dict=True)
    if existing:
        return {
            "name": existing.name,
            "status": existing.status,
            "sales_order": existing.sales_order,
            "total": flt(existing.total),
            "duplicate": True,
        }

    settings = get_settings()
    doc = frappe.new_doc("WhatsApp Order")
    doc.message_id = message_id
    doc.sender_phone = str(data["sender_phone"]).strip()
    doc.sender_name = data.get("sender_name")
    doc.original_message = data.get("original_message")
    doc.delivery_note = data.get("delivery_note")
    doc.extraction_method = data.get("extraction_method") or "agent"
    doc.received_at = now_datetime()
    doc.currency = frappe.get_cached_value(
        "Company", settings.company, "default_currency") if settings.company else "INR"

    customer = _resolve_customer(data, doc.sender_phone)
    if customer:
        doc.customer = customer
        doc.customer_confidence = flt(data.get("customer_confidence") or 0) * 100

    for raw in data.get("lines") or []:
        _append_line(doc, raw, settings)

    for issue in data.get("issues") or []:
        doc.append("issues", {
            "severity": _severity(issue.get("severity")),
            "code": issue.get("code"),
            "message": issue.get("message"),
            "line_no": cint(issue.get("line_no")) or 0,
        })

    _validate_order(doc, settings)

    doc.status = "Needs Review"
    doc.flags.ignore_permissions = True
    doc.insert()

    if _should_autopost(doc, settings):
        try:
            doc.reload()
            doc.make_sales_order_and_mark()
        except Exception as exc:
            doc.db_set("status", "Failed")
            doc.db_set("error_message", str(exc)[:500])
            frappe.log_error(frappe.get_traceback(),
                             f"WhatsApp Order {doc.name} auto-post failed")

    doc.reload()
    return {
        "name": doc.name,
        "status": doc.status,
        "sales_order": doc.sales_order,
        "total": flt(doc.total),
        "currency": doc.currency,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "lines": [
            {
                "item_code": l.item_code,
                "item_name": l.item_name,
                "qty": flt(l.qty),
                "uom": l.uom,
                "rate": flt(l.rate),
                "amount": flt(l.amount),
                "requested_qty": flt(l.requested_qty),
                "requested_uom": l.requested_uom,
                "conversion_factor": flt(l.conversion_factor),
                "confidence": flt(l.confidence) / 100.0,
            }
            for l in doc.items
        ],
        "blockers": [i.message for i in doc.issues if i.severity == "Blocker"],
        "warnings": [i.message for i in doc.issues if i.severity == "Warning"],
    }


def _as_dict(payload):
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        return frappe.parse_json(payload or "{}")
    return {}


def _severity(value):
    v = (value or "info").strip().lower()
    return {"blocker": "Blocker", "warning": "Warning"}.get(v, "Info")


def _resolve_customer(data, sender_phone):
    """Trust an explicit customer, else fall back to the sender's number."""
    explicit = data.get("customer")
    if explicit and frappe.db.exists("Customer", explicit):
        return explicit

    digits = normalise_phone(sender_phone)
    if not digits:
        return None
    tail = digits[-10:]
    for c in frappe.get_all("Customer", filters={"disabled": 0},
                            fields=["name", "mobile_no", "wa_additional_numbers"]):
        numbers = [c.mobile_no] + (c.wa_additional_numbers or "").splitlines()
        for number in numbers:
            n = normalise_phone(number)
            if n and n.endswith(tail):
                return c.name
    return None


def _append_line(doc, raw, settings):
    item_code = raw.get("item_code")
    if item_code and not frappe.db.exists("Item", item_code):
        item_code = None

    line = doc.append("items", {
        "raw_text": (raw.get("raw_text") or "")[:140],
        "item_text": (raw.get("item_text") or "")[:140],
        "item_code": item_code,
        "requested_qty": flt(raw.get("requested_qty") or raw.get("qty") or 0),
        "requested_uom": raw.get("requested_uom") or raw.get("unit"),
        "confidence": flt(raw.get("confidence") or 0) * 100,
        "match_note": raw.get("match_note"),
        "alternatives": _format_alternatives(raw.get("alternatives")),
        "currency": doc.currency,
    })

    if not item_code:
        line.qty = 0
        line.amount = 0
        return

    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
    qty, uom, factor, note = resolve_uom(
        item_code, stock_uom, line.requested_uom, line.requested_qty)
    line.qty = qty
    line.uom = uom
    line.conversion_factor = factor
    if note and not line.match_note:
        line.match_note = note
    line.rate = get_item_rate(item_code, settings.selling_price_list,
                              uom=uom, customer=doc.customer)
    line.amount = flt(line.qty) * flt(line.rate)


def _format_alternatives(alts):
    if not alts:
        return None
    out = []
    for a in alts[:5]:
        if isinstance(a, dict):
            out.append(f"{a.get('item_code')} — {a.get('item_name')} "
                       f"({flt(a.get('score', 0)) * 100:.0f}%)")
        else:
            out.append(str(a))
    return "\n".join(out)


def _validate_order(doc, settings):
    """Server-side checks against live ERPNext data."""
    if not doc.items:
        doc.append("issues", {
            "severity": "Blocker", "code": "no_lines",
            "message": _("No order lines could be read from this message."),
        })
        return

    if not doc.customer:
        doc.append("issues", {
            "severity": "Blocker", "code": "no_customer",
            "message": _("Could not identify the customer from the sender's "
                         "number or the message text."),
        })

    total = sum(flt(l.amount) for l in doc.items)

    if doc.customer and settings.enforce_credit_limit:
        limit = flt(frappe.db.get_value(
            "Customer Credit Limit", {"parent": doc.customer}, "credit_limit"))
        if limit > 0:
            outstanding = get_outstanding(doc.customer)
            available = limit - outstanding
            if total > available:
                doc.append("issues", {
                    "severity": "Blocker", "code": "credit_limit_exceeded",
                    "message": _(
                        "Order {0} exceeds available credit {1} "
                        "(limit {2}, outstanding {3})."
                    ).format(
                        frappe.format_value(total, {"fieldtype": "Currency"}),
                        frappe.format_value(available, {"fieldtype": "Currency"}),
                        frappe.format_value(limit, {"fieldtype": "Currency"}),
                        frappe.format_value(outstanding, {"fieldtype": "Currency"}),
                    ),
                })

    if settings.warehouse:
        for idx, line in enumerate(doc.items, start=1):
            if not line.item_code:
                continue
            available = flt(frappe.db.get_value(
                "Bin", {"item_code": line.item_code,
                        "warehouse": settings.warehouse}, "actual_qty"))
            if flt(line.qty) > available:
                doc.append("issues", {
                    "severity": "Blocker" if settings.enforce_stock else "Warning",
                    "code": "insufficient_stock", "line_no": idx,
                    "message": _("{0}: asked {1} {2}, available {3}.").format(
                        line.item_code, flt(line.qty), line.uom, available),
                })


def _should_autopost(doc, settings):
    if not doc.customer:
        return False
    if any(i.severity == "Blocker" for i in doc.issues):
        return False
    if not doc.items or any(not l.item_code for l in doc.items):
        return False
    threshold = flt(settings.autopost_confidence or 0.82) * 100
    return all(flt(l.confidence) >= threshold for l in doc.items)


# --------------------------------------------------------------- scheduler

def expire_stale_orders():
    """Close out unreviewed orders so the queue reflects real work."""
    settings = get_settings()
    days = cint(settings.stale_order_days) or 30
    cutoff = add_days(nowdate(), -days)
    stale = frappe.get_all(
        "WhatsApp Order",
        filters={"status": "Needs Review", "creation": ["<", cutoff]},
        pluck="name",
    )
    for name in stale:
        frappe.db.set_value("WhatsApp Order", name, {
            "status": "Rejected",
            "error_message": f"Auto-expired after {days} days without review",
        })
    if stale:
        frappe.db.commit()
    return len(stale)
