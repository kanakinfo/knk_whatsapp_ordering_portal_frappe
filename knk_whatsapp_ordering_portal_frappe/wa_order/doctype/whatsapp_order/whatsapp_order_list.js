frappe.listview_settings["WhatsApp Order"] = {
    add_fields: ["status", "total", "customer", "sales_order"],
    get_indicator(doc) {
        const map = {
            "Pending": ["Pending", "orange", "status,=,Pending"],
            "Needs Review": ["Needs Review", "orange", "status,=,Needs Review"],
            "Auto Posted": ["Auto Posted", "green", "status,=,Auto Posted"],
            "Approved": ["Approved", "blue", "status,=,Approved"],
            "Rejected": ["Rejected", "gray", "status,=,Rejected"],
            "Failed": ["Failed", "red", "status,=,Failed"],
        };
        return map[doc.status] || ["Unknown", "gray", ""];
    },
    onload(listview) {
        listview.page.add_inner_button(__("Needs Review"), () => {
            listview.filter_area.add([[
                "WhatsApp Order", "status", "=", "Needs Review",
            ]]);
        });
    },
};
