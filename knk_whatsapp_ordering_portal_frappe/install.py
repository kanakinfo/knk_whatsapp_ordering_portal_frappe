"""Install-time setup: custom fields and default settings.

Run on install and on every migrate, so adding a field later only needs a
`bench migrate`.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Item": [
        {
            "fieldname": "wa_order_section",
            "label": "WhatsApp Ordering",
            "fieldtype": "Section Break",
            "insert_after": "description",
            "collapsible": 1,
        },
        {
            "fieldname": "dealer_aliases",
            "label": "Dealer Aliases",
            "fieldtype": "Table",
            "options": "Item Dealer Alias",
            "insert_after": "wa_order_section",
            "description": (
                "Names dealers actually type for this item, including "
                "vernacular spellings and common misspellings. This is the "
                "single biggest driver of match accuracy."
            ),
        },
        {
            "fieldname": "wa_exclude",
            "label": "Exclude from WhatsApp ordering",
            "fieldtype": "Check",
            "insert_after": "dealer_aliases",
            "default": "0",
        },
    ],
    "Customer": [
        {
            "fieldname": "wa_order_section",
            "label": "WhatsApp Ordering",
            "fieldtype": "Section Break",
            "insert_after": "mobile_no",
            "collapsible": 1,
        },
        {
            "fieldname": "wa_additional_numbers",
            "label": "Additional WhatsApp Numbers",
            "fieldtype": "Small Text",
            "insert_after": "wa_order_section",
            "description": "One number per line. Any of these may place orders "
                           "for this customer.",
        },
        {
            "fieldname": "wa_aliases",
            "label": "Shop Name Aliases",
            "fieldtype": "Small Text",
            "insert_after": "wa_additional_numbers",
            "description": "One per line, e.g. 'sharma store', 'sharma ji'.",
        },
    ],
    "Sales Order": [
        {
            "fieldname": "wa_order_ref",
            "label": "WhatsApp Order",
            "fieldtype": "Link",
            "options": "WhatsApp Order",
            "insert_after": "po_no",
            "read_only": 1,
            "allow_on_submit": 1,
        },
    ],
}


NUMBER_CARDS = [
    {
        "name": "WA Orders Needing Review",
        "label": "Needs Review",
        "filters_json": '[["WhatsApp Order","status","=","Needs Review",false]]',
        "color": "#ff8c00",
    },
    {
        "name": "WA Orders Auto Posted Today",
        "label": "Auto Posted Today",
        "filters_json": (
            '[["WhatsApp Order","status","=","Auto Posted",false],'
            '["WhatsApp Order","creation","Timespan","today",false]]'
        ),
        "color": "#1a7f4b",
    },
    {
        "name": "WA Orders Failed",
        "label": "Failed",
        "filters_json": '[["WhatsApp Order","status","=","Failed",false]]',
        "color": "#b4342a",
    },
]


def after_install():
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    _ensure_settings()
    _ensure_number_cards()
    frappe.db.commit()


def _ensure_number_cards():
    for card in NUMBER_CARDS:
        if frappe.db.exists("Number Card", card["name"]):
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Number Card",
                "name": card["name"],
                "label": card["label"],
                "type": "Document Type",
                "document_type": "WhatsApp Order",
                "function": "Count",
                "filters_json": card["filters_json"],
                "is_public": 1,
                "show_percentage_stats": 1,
                "stats_time_interval": "Daily",
                "color": card["color"],
            })
            doc.insert(ignore_permissions=True)
        except Exception:
            # A missing number card must never block an install.
            frappe.log_error(frappe.get_traceback(),
                             f"Could not create Number Card {card['name']}")


def _ensure_settings():
    """Seed sensible defaults so the app works the moment it is installed."""
    settings = frappe.get_single("WhatsApp Order Settings")
    changed = False

    if not settings.company:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            company = frappe.db.get_value("Company", {}, "name")
        if company:
            settings.company = company
            changed = True

    if not settings.selling_price_list:
        settings.selling_price_list = (
            frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
            or "Standard Selling"
        )
        changed = True

    if not settings.warehouse and settings.company:
        settings.warehouse = frappe.db.get_value(
            "Warehouse", {"company": settings.company, "is_group": 0}, "name"
        )
        changed = True

    if not settings.autopost_confidence:
        settings.autopost_confidence = 0.82
        changed = True
    if not settings.match_accept_threshold:
        settings.match_accept_threshold = 0.72
        changed = True
    if not settings.stale_order_days:
        settings.stale_order_days = 30
        changed = True

    if changed:
        settings.flags.ignore_mandatory = True
        settings.save(ignore_permissions=True)


def before_uninstall():
    """Remove our custom fields so uninstall leaves a clean instance."""
    for doctype, fields in CUSTOM_FIELDS.items():
        for field in fields:
            name = f"{doctype}-{field['fieldname']}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, ignore_permissions=True,
                                  force=True)
    frappe.db.commit()
