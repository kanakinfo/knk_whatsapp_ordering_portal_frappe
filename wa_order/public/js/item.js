// Quick way to teach the matcher a new dealer name without leaving the Item.
frappe.ui.form.on("Item", {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__("Add Dealer Alias"), () => {
            frappe.prompt(
                [{
                    fieldname: "alias",
                    label: __("What do dealers call this?"),
                    fieldtype: "Data",
                    reqd: 1,
                    description: __("e.g. 'glucose biscuit', 'doodh', a common misspelling"),
                }],
                (values) => {
                    frm.add_child("dealer_aliases", { alias: values.alias });
                    frm.refresh_field("dealer_aliases");
                    frm.save();
                },
                __("Add Dealer Alias"), __("Add")
            );
        }, __("WhatsApp"));
    },
});
