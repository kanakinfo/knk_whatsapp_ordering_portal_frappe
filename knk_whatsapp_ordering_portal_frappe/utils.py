"""Shared helpers: trade-unit synonyms, pricing, catalogue assembly.

The synonym groups exist because dealers type "cs" / "peti" / "ctn" while a
client's UOM Conversion Detail usually defines only one spelling, typically
"Box" or "Case". Normalising through these groups means the client's master
data does not have to list every variant a dealer might use.
"""
import frappe
from frappe.utils import flt

UNIT_GROUPS = [
    {"case", "cases", "cs", "ctn", "ctns", "carton", "cartons",
     "box", "boxes", "peti", "petti", "crate", "crates", "bale", "bales"},
    {"dozen", "dozens", "dz", "darjan", "darzan"},
    {"packet", "packets", "pkt", "pkts", "ptk", "pack", "packs"},
    {"piece", "pieces", "pc", "pcs", "nos", "no", "unit", "units", "each"},
    {"bag", "bags", "bora", "boras", "sack", "sacks"},
    {"bottle", "bottles", "btl", "btls"},
    {"pouch", "pouches"},
    {"tin", "tins", "can", "cans"},
    {"jar", "jars"},
    {"tube", "tubes"},
    {"bar", "bars"},
    {"cup", "cups"},
    {"strip", "strips"},
    {"kg", "kgs", "kilo", "kilos", "kilogram", "kilograms"},
    {"litre", "litres", "liter", "liters", "ltr", "ltrs", "l"},
]

_LOOKUP = {}
for _group in UNIT_GROUPS:
    for _word in _group:
        _LOOKUP[_word] = _group


def unit_variants(unit_text):
    """Every spelling meaning the same trade unit, most specific first."""
    if not unit_text:
        return []
    u = str(unit_text).strip().lower()
    out = [u]
    group = _LOOKUP.get(u)
    if group:
        out.extend(sorted(group - {u}))
    # A naive rstrip("s") turns "cs" into "c"; only singularise real plurals.
    if len(u) > 3 and u.endswith("s") and not u.endswith("ss"):
        singular = u[:-2] if u.endswith(("xes", "ses", "ches")) else u[:-1]
        if singular not in out:
            out.append(singular)
    return out


def item_uom_conversions(item_code):
    """{lowercased uom name: conversion factor} from UOM Conversion Detail."""
    rows = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item_code, "parenttype": "Item"},
        fields=["uom", "conversion_factor"],
    )
    return {
        (r.uom or "").strip().lower(): flt(r.conversion_factor)
        for r in rows
        if r.uom and flt(r.conversion_factor) > 0
    }


def resolve_uom(item_code, stock_uom, requested_uom, requested_qty):
    """Convert a dealer's trade unit into the item's stock UOM.

    Returns (qty, uom, conversion_factor, note). note is None when clean.
    """
    qty = flt(requested_qty)
    if not requested_uom:
        return qty, stock_uom, 1.0, None

    variants = unit_variants(requested_uom)
    if set(unit_variants(stock_uom)).intersection(variants):
        return qty, stock_uom, 1.0, None

    conversions = item_uom_conversions(item_code)
    for variant in variants:
        if variant in conversions:
            factor = conversions[variant]
            return qty * factor, stock_uom, factor, None

    note = (
        f"'{requested_uom}' is not a defined UOM for {item_code} "
        f"(stock UOM {stock_uom}); treated as {stock_uom}"
    )
    return qty, stock_uom, 1.0, note


def get_item_rate(item_code, price_list, uom=None, customer=None):
    """Price list rate for an item, preferring a UOM-specific price."""
    if not price_list:
        return 0.0

    filters = {
        "item_code": item_code,
        "price_list": price_list,
        "selling": 1,
    }
    rows = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["price_list_rate", "uom", "customer", "valid_from", "valid_upto"],
        order_by="valid_from desc",
    )
    if not rows:
        return 0.0

    def pick(predicate):
        for r in rows:
            if predicate(r):
                return flt(r.price_list_rate)
        return None

    # Most specific first: this customer + this UOM, then either, then any.
    for predicate in (
        lambda r: customer and r.customer == customer and uom and r.uom == uom,
        lambda r: customer and r.customer == customer,
        lambda r: uom and r.uom == uom,
        lambda r: not r.customer,
        lambda r: True,
    ):
        found = pick(predicate)
        if found is not None:
            return found
    return 0.0


def get_settings():
    return frappe.get_single("WhatsApp Order Settings")


def normalise_phone(raw):
    """Digits only, with an assumed +91 when a bare 10-digit number is given."""
    if not raw:
        return None
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return digits or None
