import frappe
from frappe.model.document import Document


class WhatsAppOrderSettings(Document):
    def validate(self):
        if not (0 < (self.autopost_confidence or 0) <= 1):
            frappe.throw("Auto-post Confidence must be between 0 and 1.")
        if not (0 < (self.match_accept_threshold or 0) <= 1):
            frappe.throw("Match Accept Threshold must be between 0 and 1.")
        if self.match_accept_threshold > self.autopost_confidence:
            frappe.throw(
                "Match Accept Threshold cannot be higher than Auto-post "
                "Confidence, or no line could ever post automatically."
            )
        if self.warehouse and self.company:
            wh_company = frappe.db.get_value("Warehouse", self.warehouse, "company")
            if wh_company and wh_company != self.company:
                frappe.throw(
                    f"Warehouse {self.warehouse} belongs to {wh_company}, "
                    f"not {self.company}."
                )
