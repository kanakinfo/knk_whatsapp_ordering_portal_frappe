"""Unit tests for the UOM and pricing logic, run without a Frappe bench.

    python3 -m pytest tests/test_utils.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stub_frappe  # noqa: E402

DB = stub_frappe.install()

from wa_order.utils import (  # noqa: E402
    get_item_rate,
    normalise_phone,
    resolve_uom,
    unit_variants,
)


@pytest.fixture(autouse=True)
def seed():
    DB.set("Item", [
        {"name": "FG-BIS-001", "item_name": "Sunfield Glucose 100g",
         "stock_uom": "Packet"},
        {"name": "FG-STP-003", "item_name": "Harvest Basmati Rice 5kg",
         "stock_uom": "Bag"},
    ])
    DB.set("UOM Conversion Detail", [
        {"parent": "FG-BIS-001", "parenttype": "Item", "uom": "Case",
         "conversion_factor": 48},
        {"parent": "FG-BIS-001", "parenttype": "Item", "uom": "Dozen",
         "conversion_factor": 12},
        {"parent": "FG-STP-003", "parenttype": "Item", "uom": "Case",
         "conversion_factor": 4},
    ])
    DB.set("Item Price", [
        {"item_code": "FG-BIS-001", "price_list": "Standard Selling",
         "price_list_rate": 10, "selling": 1, "uom": None, "customer": None},
        {"item_code": "FG-BIS-001", "price_list": "Standard Selling",
         "price_list_rate": 460, "selling": 1, "uom": "Case", "customer": None},
        {"item_code": "FG-BIS-001", "price_list": "Standard Selling",
         "price_list_rate": 9, "selling": 1, "uom": None,
         "customer": "CUST-0001"},
    ])
    yield


class TestUnitVariants:
    @pytest.mark.parametrize("unit", ["case", "cs", "ctn", "peti", "box", "carton"])
    def test_case_family(self, unit):
        assert "case" in unit_variants(unit)

    def test_cs_is_not_singularised_to_c(self):
        """rstrip('s') would turn 'cs' into 'c' and lose the conversion."""
        assert "c" not in unit_variants("cs")

    def test_plurals_singularise(self):
        assert "carton" in unit_variants("cartons")
        assert "box" in unit_variants("boxes")

    def test_unknown_unit_returns_itself(self):
        assert unit_variants("truckload") == ["truckload"]

    def test_empty(self):
        assert unit_variants(None) == []


class TestResolveUom:
    def test_case_converts(self):
        qty, uom, factor, note = resolve_uom("FG-BIS-001", "Packet", "case", 5)
        assert (qty, uom, factor, note) == (240, "Packet", 48, None)

    @pytest.mark.parametrize("unit", ["cs", "ctn", "peti", "box", "carton", "CASE"])
    def test_every_case_synonym_hits_the_same_factor(self, unit):
        """The item defines only 'Case'; dealers type anything."""
        qty, _, factor, note = resolve_uom("FG-BIS-001", "Packet", unit, 5)
        assert factor == 48, unit
        assert qty == 240, unit
        assert note is None, unit

    def test_stock_uom_named_directly(self):
        qty, uom, factor, note = resolve_uom("FG-BIS-001", "Packet", "packet", 10)
        assert (qty, factor, note) == (10, 1.0, None)

    def test_stock_uom_synonym(self):
        """'pkt' means the stock UOM 'Packet'."""
        qty, _, factor, note = resolve_uom("FG-BIS-001", "Packet", "pkt", 10)
        assert (qty, factor, note) == (10, 1.0, None)

    def test_no_unit_given(self):
        qty, uom, factor, note = resolve_uom("FG-BIS-001", "Packet", None, 7)
        assert (qty, uom, factor, note) == (7, "Packet", 1.0, None)

    def test_bora_is_a_bag(self):
        qty, uom, factor, note = resolve_uom("FG-STP-003", "Bag", "bora", 4)
        assert (qty, uom, factor) == (4, "Bag", 1.0)
        assert note is None

    def test_undefined_unit_is_flagged_not_assumed(self):
        qty, uom, factor, note = resolve_uom("FG-STP-003", "Bag", "truckload", 4)
        assert qty == 4 and factor == 1.0
        assert note and "truckload" in note

    def test_different_items_have_different_factors(self):
        """The same word must resolve per item, not globally."""
        _, _, biscuit, _ = resolve_uom("FG-BIS-001", "Packet", "case", 1)
        _, _, rice, _ = resolve_uom("FG-STP-003", "Bag", "case", 1)
        assert biscuit == 48 and rice == 4


class TestPricing:
    def test_plain_list_rate(self):
        assert get_item_rate("FG-BIS-001", "Standard Selling") == 10

    def test_uom_specific_rate_wins(self):
        assert get_item_rate("FG-BIS-001", "Standard Selling", uom="Case") == 460

    def test_customer_specific_rate_wins(self):
        assert get_item_rate("FG-BIS-001", "Standard Selling",
                             customer="CUST-0001") == 9

    def test_unknown_item_is_zero(self):
        assert get_item_rate("NOPE", "Standard Selling") == 0.0

    def test_no_price_list(self):
        assert get_item_rate("FG-BIS-001", None) == 0.0


class TestPhone:
    def test_adds_country_code(self):
        assert normalise_phone("9812345671") == "919812345671"

    def test_strips_formatting(self):
        assert normalise_phone("+91 98123-45671") == "919812345671"

    def test_empty(self):
        assert normalise_phone(None) is None
        assert normalise_phone("") is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
