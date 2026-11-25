// Review screen for a WhatsApp order.
frappe.ui.form.on("WhatsApp Order", {
    refresh(frm) {
        frm.trigger("set_status_indicator");
        frm.trigger("add_action_buttons");
        frm.trigger("show_blocker_banner");
        frm.trigger("paint_confidence");
    },

    set_status_indicator(frm) {
        const colours = {
            "Pending": "orange",
            "Needs Review": "orange",
            "Auto Posted": "green",
            "Approved": "blue",
            "Rejected": "gray",
            "Failed": "red",
        };
        if (frm.doc.status) {
            frm.page.set_indicator(frm.doc.status, colours[frm.doc.status] || "gray");
        }
    },

    add_action_buttons(frm) {
        if (frm.is_new()) return;

        if (frm.doc.sales_order) {
            frm.add_custom_button(__("Sales Order"), () => {
                frappe.set_route("Form", "Sales Order", frm.doc.sales_order);
            }, __("View"));
        }

        const open = ["Pending", "Needs Review", "Failed"].includes(frm.doc.status);
        if (!open) return;

        const blockers = (frm.doc.issues || []).filter(i => i.severity === "Blocker");

        frm.page.set_primary_action(__("Approve & Create Sales Order"), () => {
            approve(frm, false);
        });

        if (blockers.length) {
            frm.add_custom_button(__("Approve Anyway"), () => {
                frappe.confirm(
                    __("This order has {0} unresolved blocker(s). Post it regardless?",
                       [blockers.length]),
                    () => approve(frm, true)
                );
            });
        }

        frm.add_custom_button(__("Reject"), () => {
            frappe.prompt(
                [{ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text" }],
                (values) => {
                    frm.call("reject", { reason: values.reason })
                        .then(() => frm.reload_doc());
                },
                __("Reject this order"), __("Reject")
            );
        });
    },

    show_blocker_banner(frm) {
        frm.dashboard.clear_comment();
        const issues = frm.doc.issues || [];
        const blockers = issues.filter(i => i.severity === "Blocker");
        const warnings = issues.filter(i => i.severity === "Warning");

        if (blockers.length) {
            frm.dashboard.add_comment(
                "<b>" + __("Blocked") + ":</b><br>" +
                blockers.map(b => "• " + frappe.utils.escape_html(b.message)).join("<br>"),
                "red", true
            );
        } else if (warnings.length) {
            frm.dashboard.add_comment(
                "<b>" + __("Check before posting") + ":</b><br>" +
                warnings.map(w => "• " + frappe.utils.escape_html(w.message)).join("<br>"),
                "orange", true
            );
        }
    },

    // Tint low-confidence rows so the eye lands on what needs a decision.
    paint_confidence(frm) {
        if (!frm.fields_dict.items || !frm.fields_dict.items.grid) return;
        setTimeout(() => {
            (frm.doc.items || []).forEach(row => {
                const $row = frm.fields_dict.items.grid.grid_rows_by_docname[row.name];
                if (!$row || !$row.row) return;
                const c = flt(row.confidence);
                let colour = "";
                if (!row.item_code || c < 45) colour = "var(--red-50, #fdeeec)";
                else if (c < 82) colour = "var(--yellow-50, #fdf7ea)";
                $row.row.css("background-color", colour);
            });
        }, 100);
    },
});

function approve(frm, ignore_blockers) {
    frappe.dom.freeze(__("Creating Sales Order…"));
    frm.call("approve", { ignore_blockers: ignore_blockers ? 1 : 0 })
        .then(() => {
            frappe.dom.unfreeze();
            frm.reload_doc();
        })
        .catch(() => frappe.dom.unfreeze());
}

// Correcting the item re-prices and re-converts server-side; refresh after save.
frappe.ui.form.on("WhatsApp Order Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;
        frappe.show_alert({
            message: __("Quantity and rate will recalculate when you save."),
            indicator: "blue",
        });
    },
});
