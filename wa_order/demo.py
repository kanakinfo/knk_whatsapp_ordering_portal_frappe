"""Demo master data for a fresh ERPNext instance.

    bench --site <site> execute wa_order.demo.install

Creates UOMs, items with dealer aliases and case conversions, customers with
WhatsApp numbers and credit limits, opening stock and opening receivables -
everything the demo messages need.

Safe to re-run: every step checks for an existing record first.
Remove it all with:

    bench --site <site> execute wa_order.demo.uninstall

Invented house brands on purpose - demo data you ship should not carry third
party trademarks.
"""
import frappe
from frappe.utils import flt, nowdate, add_days

ITEM_GROUP = "WA Demo FMCG"
BASE_UOMS = ["Packet", "Bottle", "Pouch", "Bag", "Bar", "Can", "Cup", "Jar",
             "Tube", "Case", "Dozen", "Crate"]

DEMO_ITEMS = [
    {
        "item_code": "FG-BIS-001",
        "item_name": "Sunfield Glucose Biscuit 100g",
        "stock_uom": "Packet",
        "rate": 10.0,
        "opening_qty": 4800.0,
        "brand": "Sunfield",
        "aliases": [
            "sunfield glucose",
            "sunfield g",
            "glucose biscuit",
            "sunfield biscuit 100g",
            "sf glucose",
            "sunfeild glucose"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 48.0
        }
    },
    {
        "item_code": "FG-BIS-002",
        "item_name": "Sunfield Glucose Biscuit 250g",
        "stock_uom": "Packet",
        "rate": 25.0,
        "opening_qty": 1900.0,
        "brand": "Sunfield",
        "aliases": [
            "sunfield glucose 250",
            "sunfield g big",
            "glucose 250g"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BIS-003",
        "item_name": "Sunfield Marie Light 150g",
        "stock_uom": "Packet",
        "rate": 30.0,
        "opening_qty": 1400.0,
        "brand": "Sunfield",
        "aliases": [
            "marie",
            "marie light",
            "sunfield marie",
            "mari biscuit",
            "marie biscuit"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BIS-004",
        "item_name": "Tara Cream Biscuit Orange 120g",
        "stock_uom": "Packet",
        "rate": 20.0,
        "opening_qty": 2100.0,
        "brand": "Tara",
        "aliases": [
            "tara orange cream",
            "orange cream",
            "tara cream orange",
            "orange biscuit"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BIS-005",
        "item_name": "Tara Cream Biscuit Chocolate 120g",
        "stock_uom": "Packet",
        "rate": 20.0,
        "opening_qty": 2600.0,
        "brand": "Tara",
        "aliases": [
            "tara choco cream",
            "chocolate cream",
            "choco cream",
            "tara cream chocolate"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BIS-006",
        "item_name": "Tara Salted Cracker 200g",
        "stock_uom": "Packet",
        "rate": 35.0,
        "opening_qty": 900.0,
        "brand": "Tara",
        "aliases": [
            "salted cracker",
            "tara cracker",
            "namkeen biscuit",
            "salty biscuit"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BEV-001",
        "item_name": "Amrit Mango Drink 200ml",
        "stock_uom": "Bottle",
        "rate": 20.0,
        "opening_qty": 6000.0,
        "brand": "Amrit",
        "aliases": [
            "amrit mango",
            "mango drink",
            "aam juice",
            "amrit aam",
            "mango 200ml"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BEV-002",
        "item_name": "Amrit Mango Drink 600ml",
        "stock_uom": "Bottle",
        "rate": 50.0,
        "opening_qty": 2400.0,
        "brand": "Amrit",
        "aliases": [
            "amrit mango big",
            "mango 600",
            "mango drink 600ml"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-BEV-003",
        "item_name": "Amrit Orange Drink 200ml",
        "stock_uom": "Bottle",
        "rate": 20.0,
        "opening_qty": 3600.0,
        "brand": "Amrit",
        "aliases": [
            "amrit orange",
            "orange drink",
            "santra juice",
            "orange 200ml"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BEV-004",
        "item_name": "Nutrolite Lemon Soda 500ml",
        "stock_uom": "Bottle",
        "rate": 35.0,
        "opening_qty": 1800.0,
        "brand": "Nutrolite",
        "aliases": [
            "lemon soda",
            "nimbu soda",
            "nutrolite lemon",
            "lime soda"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-BEV-005",
        "item_name": "Nutrolite Energy Drink 250ml",
        "stock_uom": "Can",
        "rate": 60.0,
        "opening_qty": 1200.0,
        "brand": "Nutrolite",
        "aliases": [
            "energy drink",
            "nutrolite energy",
            "energy can"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-BEV-006",
        "item_name": "Amrit Packaged Water 1L",
        "stock_uom": "Bottle",
        "rate": 20.0,
        "opening_qty": 9600.0,
        "brand": "Amrit",
        "aliases": [
            "water",
            "pani",
            "mineral water",
            "amrit water",
            "water bottle 1l"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-DRY-001",
        "item_name": "Milkmoor Toned Milk 500ml",
        "stock_uom": "Pouch",
        "rate": 27.0,
        "opening_qty": 2000.0,
        "brand": "Milkmoor",
        "aliases": [
            "toned milk",
            "milkmoor milk",
            "doodh",
            "milk pouch",
            "milkmoor toned"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Crate": 24.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-DRY-002",
        "item_name": "Milkmoor Full Cream Milk 500ml",
        "stock_uom": "Pouch",
        "rate": 33.0,
        "opening_qty": 1600.0,
        "brand": "Milkmoor",
        "aliases": [
            "full cream milk",
            "milkmoor full cream",
            "fc milk",
            "malai doodh"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Crate": 24.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-DRY-003",
        "item_name": "Milkmoor Curd 400g",
        "stock_uom": "Cup",
        "rate": 30.0,
        "opening_qty": 800.0,
        "brand": "Milkmoor",
        "aliases": [
            "curd",
            "dahi",
            "milkmoor curd",
            "yogurt"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-DRY-004",
        "item_name": "Milkmoor Butter 100g",
        "stock_uom": "Packet",
        "rate": 58.0,
        "opening_qty": 600.0,
        "brand": "Milkmoor",
        "aliases": [
            "butter",
            "makhan",
            "milkmoor butter"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-DRY-005",
        "item_name": "Milkmoor Paneer 200g",
        "stock_uom": "Packet",
        "rate": 95.0,
        "opening_qty": 300.0,
        "brand": "Milkmoor",
        "aliases": [
            "paneer",
            "milkmoor paneer",
            "cottage cheese"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-STP-001",
        "item_name": "Goldfield Refined Oil 1L",
        "stock_uom": "Pouch",
        "rate": 145.0,
        "opening_qty": 1400.0,
        "brand": "Goldfield",
        "aliases": [
            "refined oil",
            "tel",
            "goldfield oil",
            "cooking oil",
            "refine oil"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 10.0
        }
    },
    {
        "item_code": "FG-STP-002",
        "item_name": "Goldfield Mustard Oil 1L",
        "stock_uom": "Pouch",
        "rate": 165.0,
        "opening_qty": 900.0,
        "brand": "Goldfield",
        "aliases": [
            "mustard oil",
            "sarso tel",
            "kachi ghani",
            "goldfield mustard"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 10.0
        }
    },
    {
        "item_code": "FG-STP-003",
        "item_name": "Harvest Basmati Rice 5kg",
        "stock_uom": "Bag",
        "rate": 520.0,
        "opening_qty": 400.0,
        "brand": "Harvest",
        "aliases": [
            "basmati",
            "basmati rice",
            "chawal",
            "harvest rice",
            "rice 5kg"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 4.0
        }
    },
    {
        "item_code": "FG-STP-004",
        "item_name": "Harvest Atta 5kg",
        "stock_uom": "Bag",
        "rate": 240.0,
        "opening_qty": 700.0,
        "brand": "Harvest",
        "aliases": [
            "atta",
            "wheat flour",
            "harvest atta",
            "flour 5kg"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 4.0
        }
    },
    {
        "item_code": "FG-STP-005",
        "item_name": "Harvest Toor Dal 1kg",
        "stock_uom": "Packet",
        "rate": 160.0,
        "opening_qty": 1100.0,
        "brand": "Harvest",
        "aliases": [
            "toor dal",
            "arhar dal",
            "tur dal",
            "dal",
            "harvest toor"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-STP-006",
        "item_name": "Harvest Sugar 1kg",
        "stock_uom": "Packet",
        "rate": 48.0,
        "opening_qty": 2000.0,
        "brand": "Harvest",
        "aliases": [
            "sugar",
            "cheeni",
            "shakkar",
            "harvest sugar"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 20.0
        }
    },
    {
        "item_code": "FG-HPC-001",
        "item_name": "Pureglow Bath Soap 100g",
        "stock_uom": "Bar",
        "rate": 38.0,
        "opening_qty": 3400.0,
        "brand": "Pureglow",
        "aliases": [
            "bath soap",
            "sabun",
            "pureglow soap",
            "soap 100g",
            "nahane ka sabun"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 48.0
        }
    },
    {
        "item_code": "FG-HPC-002",
        "item_name": "Pureglow Handwash 200ml",
        "stock_uom": "Bottle",
        "rate": 85.0,
        "opening_qty": 700.0,
        "brand": "Pureglow",
        "aliases": [
            "handwash",
            "hand wash",
            "pureglow handwash"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-HPC-003",
        "item_name": "Sparkle Detergent Powder 1kg",
        "stock_uom": "Packet",
        "rate": 110.0,
        "opening_qty": 1500.0,
        "brand": "Sparkle",
        "aliases": [
            "detergent",
            "washing powder",
            "sparkle powder",
            "surf",
            "kapde ka powder"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-HPC-004",
        "item_name": "Sparkle Detergent Bar 250g",
        "stock_uom": "Bar",
        "rate": 22.0,
        "opening_qty": 2800.0,
        "brand": "Sparkle",
        "aliases": [
            "detergent bar",
            "washing bar",
            "sparkle bar",
            "kapde ka sabun"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 30.0
        }
    },
    {
        "item_code": "FG-HPC-005",
        "item_name": "Sparkle Dishwash Gel 500ml",
        "stock_uom": "Bottle",
        "rate": 99.0,
        "opening_qty": 900.0,
        "brand": "Sparkle",
        "aliases": [
            "dishwash",
            "bartan liquid",
            "dish gel",
            "sparkle dishwash"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 12.0
        }
    },
    {
        "item_code": "FG-HPC-006",
        "item_name": "Freshmint Toothpaste 100g",
        "stock_uom": "Tube",
        "rate": 62.0,
        "opening_qty": 1600.0,
        "brand": "Freshmint",
        "aliases": [
            "toothpaste",
            "manjan",
            "freshmint paste",
            "colgate",
            "tooth paste"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-SNK-001",
        "item_name": "Crunchos Potato Chips Salted 52g",
        "stock_uom": "Packet",
        "rate": 20.0,
        "opening_qty": 3000.0,
        "brand": "Crunchos",
        "aliases": [
            "chips",
            "potato chips",
            "salted chips",
            "crunchos salted",
            "aloo chips"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 40.0
        }
    },
    {
        "item_code": "FG-SNK-002",
        "item_name": "Crunchos Potato Chips Masala 52g",
        "stock_uom": "Packet",
        "rate": 20.0,
        "opening_qty": 3200.0,
        "brand": "Crunchos",
        "aliases": [
            "masala chips",
            "crunchos masala",
            "chips masala"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 40.0
        }
    },
    {
        "item_code": "FG-SNK-003",
        "item_name": "Namkeen House Mixture 200g",
        "stock_uom": "Packet",
        "rate": 45.0,
        "opening_qty": 1200.0,
        "brand": "Namkeen House",
        "aliases": [
            "mixture",
            "namkeen",
            "mix namkeen",
            "namkeen mixture"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-SNK-004",
        "item_name": "Namkeen House Aloo Bhujia 200g",
        "stock_uom": "Packet",
        "rate": 48.0,
        "opening_qty": 1000.0,
        "brand": "Namkeen House",
        "aliases": [
            "bhujia",
            "aloo bhujia",
            "bhujiya",
            "namkeen bhujia"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-SNK-005",
        "item_name": "Crunchos Corn Puffs 40g",
        "stock_uom": "Packet",
        "rate": 10.0,
        "opening_qty": 4000.0,
        "brand": "Crunchos",
        "aliases": [
            "corn puffs",
            "puffs",
            "kurkure",
            "corn snack"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 60.0
        }
    },
    {
        "item_code": "FG-TEA-001",
        "item_name": "Hilltop Tea 250g",
        "stock_uom": "Packet",
        "rate": 135.0,
        "opening_qty": 1300.0,
        "brand": "Hilltop",
        "aliases": [
            "tea",
            "chai patti",
            "hilltop tea",
            "chai",
            "tea 250g"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    },
    {
        "item_code": "FG-TEA-002",
        "item_name": "Hilltop Tea 1kg",
        "stock_uom": "Packet",
        "rate": 500.0,
        "opening_qty": 400.0,
        "brand": "Hilltop",
        "aliases": [
            "tea 1kg",
            "hilltop tea big",
            "chai patti 1kg"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 10.0
        }
    },
    {
        "item_code": "FG-TEA-003",
        "item_name": "Hilltop Instant Coffee 50g",
        "stock_uom": "Jar",
        "rate": 180.0,
        "opening_qty": 500.0,
        "brand": "Hilltop",
        "aliases": [
            "coffee",
            "instant coffee",
            "hilltop coffee"
        ],
        "conversions": {
            "Dozen": 12.0,
            "Case": 24.0
        }
    }
]

DEMO_CUSTOMERS = [
    {
        "name": "CUST-0001",
        "customer_name": "Sharma General Store",
        "phone": "919812345671",
        "aliases": [
            "sharma store",
            "sharma kirana",
            "sharma ji"
        ],
        "credit_limit": 150000.0,
        "opening_due": 42000.0,
        "territory": "Ludhiana"
    },
    {
        "name": "CUST-0002",
        "customer_name": "Verma Kirana & Provision",
        "phone": "919812345672",
        "aliases": [
            "verma kirana",
            "verma store",
            "verma provision"
        ],
        "credit_limit": 100000.0,
        "opening_due": 96500.0,
        "territory": "Ludhiana"
    },
    {
        "name": "CUST-0003",
        "customer_name": "New Apna Bazaar",
        "phone": "919812345673",
        "aliases": [
            "apna bazaar",
            "apna bazar",
            "new apna"
        ],
        "credit_limit": 250000.0,
        "opening_due": 38000.0,
        "territory": "Jalandhar"
    },
    {
        "name": "CUST-0004",
        "customer_name": "Singh Super Market",
        "phone": "919812345674",
        "aliases": [
            "singh super",
            "singh market",
            "singh supermarket"
        ],
        "credit_limit": 300000.0,
        "opening_due": 112000.0,
        "territory": "Jalandhar"
    },
    {
        "name": "CUST-0005",
        "customer_name": "Gupta Traders",
        "phone": "919812345675",
        "aliases": [
            "gupta traders",
            "gupta store",
            "gupta ji"
        ],
        "credit_limit": 80000.0,
        "opening_due": 15000.0,
        "territory": "Amritsar"
    },
    {
        "name": "CUST-0006",
        "customer_name": "Krishna Retail Point",
        "phone": "919812345676",
        "aliases": [
            "krishna retail",
            "krishna point",
            "krishna store"
        ],
        "credit_limit": 120000.0,
        "opening_due": 0.0,
        "territory": "Amritsar"
    },
    {
        "name": "CUST-0007",
        "customer_name": "Balaji Wholesale",
        "phone": "919812345677",
        "aliases": [
            "balaji",
            "balaji wholesale",
            "balaji w/s"
        ],
        "credit_limit": 500000.0,
        "opening_due": 210000.0,
        "territory": "Ludhiana"
    },
    {
        "name": "CUST-0008",
        "customer_name": "Mehta Daily Needs",
        "phone": "919812345678",
        "aliases": [
            "mehta daily",
            "mehta needs",
            "mehta store"
        ],
        "credit_limit": 60000.0,
        "opening_due": 9000.0,
        "territory": "Patiala"
    }
]


def _log(msg):
    print(msg)
    frappe.publish_realtime("wa_demo_progress", {"message": msg})


def _ensure_uoms():
    created = 0
    for uom in BASE_UOMS:
        if not frappe.db.exists("UOM", uom):
            frappe.get_doc({"doctype": "UOM", "uom_name": uom,
                            "must_be_whole_number": 1}).insert(ignore_permissions=True)
            created += 1
    _log(f"UOMs: {created} created, {len(BASE_UOMS) - created} already present")


def _ensure_item_group():
    if not frappe.db.exists("Item Group", ITEM_GROUP):
        parent = frappe.db.get_value("Item Group", {"is_group": 1,
                                                    "parent_item_group": ""} , "name") \
            or "All Item Groups"
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": ITEM_GROUP,
            "parent_item_group": parent,
            "is_group": 0,
        }).insert(ignore_permissions=True)
        _log(f"Item Group {ITEM_GROUP} created")


def _ensure_brands():
    brands = {i["brand"] for i in DEMO_ITEMS if i.get("brand")}
    for brand in sorted(brands):
        if not frappe.db.exists("Brand", brand):
            frappe.get_doc({"doctype": "Brand", "brand": brand}).insert(
                ignore_permissions=True)
    _log(f"Brands: {len(brands)} ensured")


def _ensure_items(price_list):
    created = updated = 0
    for row in DEMO_ITEMS:
        if frappe.db.exists("Item", row["item_code"]):
            doc = frappe.get_doc("Item", row["item_code"])
            updated += 1
        else:
            doc = frappe.new_doc("Item")
            doc.item_code = row["item_code"]
            doc.item_group = ITEM_GROUP
            doc.stock_uom = row["stock_uom"]
            doc.is_stock_item = 1
            doc.is_sales_item = 1
            created += 1

        doc.item_name = row["item_name"]
        if row.get("brand"):
            doc.brand = row["brand"]

        # UOM conversions: how many stock UOM one case / dozen represents.
        existing_uoms = {u.uom for u in (doc.uoms or [])}
        if doc.stock_uom not in existing_uoms:
            doc.append("uoms", {"uom": doc.stock_uom, "conversion_factor": 1})
        for uom, factor in (row.get("conversions") or {}).items():
            if uom not in existing_uoms:
                doc.append("uoms", {"uom": uom, "conversion_factor": flt(factor)})

        # Dealer aliases - the single biggest driver of match accuracy.
        have = {a.alias.strip().lower() for a in (doc.get("dealer_aliases") or [])
                if a.alias}
        for alias in row.get("aliases") or []:
            if alias.strip().lower() not in have:
                doc.append("dealer_aliases", {"alias": alias})

        doc.flags.ignore_mandatory = True
        doc.save(ignore_permissions=True)
        _ensure_item_price(row["item_code"], price_list, row["rate"])

    _log(f"Items: {created} created, {updated} updated")


def _ensure_item_price(item_code, price_list, rate):
    existing = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "uom": ["in", ["", None]]},
        "name")
    if existing:
        frappe.db.set_value("Item Price", existing, "price_list_rate", flt(rate))
        return
    frappe.get_doc({
        "doctype": "Item Price",
        "item_code": item_code,
        "price_list": price_list,
        "price_list_rate": flt(rate),
        "selling": 1,
    }).insert(ignore_permissions=True)


def _ensure_customers():
    created = updated = 0
    territory_root = frappe.db.get_value("Territory", {"is_group": 1}, "name") \
        or "All Territories"
    group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") \
        or "All Customer Groups"

    for row in DEMO_CUSTOMERS:
        if frappe.db.exists("Customer", row["name"]):
            doc = frappe.get_doc("Customer", row["name"])
            updated += 1
        else:
            doc = frappe.new_doc("Customer")
            doc.name = row["name"]
            doc.customer_group = group
            doc.customer_type = "Company"
            created += 1

        doc.customer_name = row["customer_name"]
        doc.mobile_no = row["phone"]
        doc.wa_aliases = "\n".join(row.get("aliases") or [])

        if row.get("territory"):
            if not frappe.db.exists("Territory", row["territory"]):
                frappe.get_doc({
                    "doctype": "Territory",
                    "territory_name": row["territory"],
                    "parent_territory": territory_root,
                    "is_group": 0,
                }).insert(ignore_permissions=True)
            doc.territory = row["territory"]

        doc.flags.ignore_mandatory = True
        doc.save(ignore_permissions=True)
        _set_credit_limit(doc.name, row.get("credit_limit"))

    _log(f"Customers: {created} created, {updated} updated")


def _set_credit_limit(customer, limit):
    if not limit:
        return
    company = frappe.db.get_single_value("WhatsApp Order Settings", "company") \
        or frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        return
    doc = frappe.get_doc("Customer", customer)
    for row in doc.get("credit_limits") or []:
        if row.company == company:
            row.credit_limit = flt(limit)
            doc.save(ignore_permissions=True)
            return
    doc.append("credit_limits", {"company": company, "credit_limit": flt(limit)})
    doc.flags.ignore_mandatory = True
    doc.save(ignore_permissions=True)


def _opening_stock(warehouse):
    """Material Receipt so the stock-cover checks have something to check."""
    if not warehouse:
        _log("Opening stock skipped: no warehouse configured in Settings")
        return
    if frappe.db.exists("Stock Entry", {"remarks": "WA demo opening stock",
                                        "docstatus": 1}):
        _log("Opening stock already posted")
        return
    try:
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"
        se.remarks = "WA demo opening stock"
        se.posting_date = nowdate()
        for row in DEMO_ITEMS:
            if not row.get("opening_qty"):
                continue
            se.append("items", {
                "item_code": row["item_code"],
                "qty": flt(row["opening_qty"]),
                "uom": row["stock_uom"],
                "stock_uom": row["stock_uom"],
                "conversion_factor": 1,
                "t_warehouse": warehouse,
                "basic_rate": flt(row["rate"]) * 0.7,
            })
        se.flags.ignore_permissions = True
        se.insert()
        se.submit()
        _log(f"Opening stock posted to {warehouse} ({se.name})")
    except Exception as exc:
        _log(f"Opening stock SKIPPED ({exc}). Stock warnings will not appear; "
             f"everything else works. Post stock manually if you want them.")


def _opening_receivables(company):
    """Submitted invoices so the credit-limit block is real, not staged."""
    targets = [(c["name"], c["opening_due"]) for c in DEMO_CUSTOMERS
               if c.get("opening_due")]
    if not targets:
        return
    if frappe.db.exists("Sales Invoice", {"remarks": "WA demo opening due",
                                          "docstatus": 1}):
        _log("Opening receivables already posted")
        return

    item = DEMO_ITEMS[0]["item_code"]
    posted = failed = 0
    for customer, amount in targets:
        try:
            si = frappe.new_doc("Sales Invoice")
            si.customer = customer
            si.company = company
            si.posting_date = add_days(nowdate(), -20)
            si.due_date = add_days(nowdate(), -5)
            si.set_posting_time = 1
            si.update_stock = 0
            si.remarks = "WA demo opening due"
            # Let ERPNext resolve the income account from company defaults.
            si.append("items", {"item_code": item, "qty": 1, "rate": flt(amount)})
            si.flags.ignore_permissions = True
            si.insert()
            si.submit()
            posted += 1
        except Exception as exc:
            failed += 1
            frappe.db.rollback()
            _log(f"  could not post opening due for {customer}: {exc}")

    if failed:
        _log(f"Opening receivables: {posted} posted, {failed} failed. "
             f"Where it failed, lower that customer's credit limit by hand to "
             f"demo the credit block.")
    else:
        _log(f"Opening receivables: {posted} invoices posted")


def install(with_stock=True, with_receivables=True):
    """Create the whole demo dataset. Safe to re-run."""
    settings = frappe.get_single("WhatsApp Order Settings")
    company = settings.company or frappe.db.get_single_value(
        "Global Defaults", "default_company")
    if not company:
        frappe.throw("Set a Company in WhatsApp Order Settings first.")
    price_list = settings.selling_price_list or "Standard Selling"

    _log(f"Installing WA demo data into {company} (price list {price_list})")
    _ensure_uoms()
    _ensure_item_group()
    _ensure_brands()
    _ensure_items(price_list)
    _ensure_customers()
    frappe.db.commit()

    if frappe.parse_json(str(with_stock).lower()):
        _opening_stock(settings.warehouse)
        frappe.db.commit()
    if frappe.parse_json(str(with_receivables).lower()):
        _opening_receivables(company)
        frappe.db.commit()

    _log("")
    _log("Done. Try sending this from the demo number on file for "
         "Sharma General Store:")
    _log("    5 case sunfield glucose 100g")
    _log("    2 peti amrit mango 200ml")
    _log("    10 packet marie")
    return "ok"


def uninstall():
    """Remove the demo dataset. Leaves anything with transactions against it."""
    removed = skipped = 0
    for row in DEMO_ITEMS:
        try:
            if frappe.db.exists("Item", row["item_code"]):
                frappe.delete_doc("Item", row["item_code"],
                                  ignore_permissions=True, force=False)
                removed += 1
        except Exception:
            skipped += 1
    for row in DEMO_CUSTOMERS:
        try:
            if frappe.db.exists("Customer", row["name"]):
                frappe.delete_doc("Customer", row["name"],
                                  ignore_permissions=True, force=False)
                removed += 1
        except Exception:
            skipped += 1
    frappe.db.commit()
    _log(f"Removed {removed}; {skipped} kept because they have transactions.")
    return "ok"
