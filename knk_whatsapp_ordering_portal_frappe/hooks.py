app_name = "knk_whatsapp_ordering_portal_frappe"
app_title = "WA Order"
app_publisher = "Your Company"
app_description = "Turns dealer WhatsApp messages into validated ERPNext Sales Orders"
app_email = "dev@yourcompany.com"
app_license = "MIT"
required_apps = ["erpnext"]

# Custom fields added to stock ERPNext doctypes (Item.dealer_aliases, and the
# WhatsApp traceability fields on Sales Order) are created here.
after_install = "knk_whatsapp_ordering_portal_frappe.install.after_install"
after_migrate = "knk_whatsapp_ordering_portal_frappe.install.after_install"
before_uninstall = "knk_whatsapp_ordering_portal_frappe.install.before_uninstall"

app_include_js = []
app_include_css = []

# v16: the desktop app icon is driven by this hook. Harmless on v15, which
# ignores hooks it does not know.
add_to_apps_screen = [
    {
        "name": "knk_whatsapp_ordering_portal_frappe",
        "logo": "/assets/knk_whatsapp_ordering_portal_frappe/images/logo.svg",
        "title": "WhatsApp Orders",
        "route": "/app/whatsapp-orders",
        "has_permission": "knk_whatsapp_ordering_portal_frappe.api.has_app_permission",
    }
]

doctype_js = {
    "Item": "public/js/item.js",
}

# Nightly tidy-up of stale drafts so the queue does not grow forever.
scheduler_events = {
    "daily": [
        "knk_whatsapp_ordering_portal_frappe.api.expire_stale_orders",
    ],
}

# Let the agent's dedicated user hit the whitelisted endpoints.
override_whitelisted_methods = {}

fixtures = []
