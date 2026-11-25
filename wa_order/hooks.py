app_name = "wa_order"
app_title = "WA Order"
app_publisher = "Your Company"
app_description = "Turns dealer WhatsApp messages into validated ERPNext Sales Orders"
app_email = "dev@yourcompany.com"
app_license = "MIT"
required_apps = ["erpnext"]

# Custom fields added to stock ERPNext doctypes (Item.dealer_aliases, and the
# WhatsApp traceability fields on Sales Order) are created here.
after_install = "wa_order.install.after_install"
after_migrate = "wa_order.install.after_install"
before_uninstall = "wa_order.install.before_uninstall"

app_include_js = []
app_include_css = []

doctype_js = {
    "Item": "public/js/item.js",
}

# Nightly tidy-up of stale drafts so the queue does not grow forever.
scheduler_events = {
    "daily": [
        "wa_order.api.expire_stale_orders",
    ],
}

# Let the agent's dedicated user hit the whitelisted endpoints.
override_whitelisted_methods = {}

fixtures = []
