"""A minimal in-memory `frappe` so the pure logic in wa_order can be tested
without a bench. Supports only what knk_whatsapp_ordering_portal_frappe.utils actually calls.

Your dev team can use this to test matching changes in seconds instead of
running a full site.
"""
from __future__ import annotations

import sys
import types


class _DotDict(dict):
    __getattr__ = dict.get

    def __setattr__(self, k, v):
        self[k] = v


def flt(value, precision=None):
    try:
        f = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(f, precision) if precision is not None else f


def cint(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


class _DB:
    """Tables are lists of dicts; filters are simple equality / 'in' / list."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def set(self, doctype, rows):
        self.tables[doctype] = [dict(r) for r in rows]

    def _match(self, row, filters):
        if not filters:
            return True
        if isinstance(filters, dict):
            items = filters.items()
        else:
            items = [(f[0], f[1]) if len(f) == 2 else (f[1], (f[2], f[3]))
                     for f in filters]
        for key, cond in items:
            value = row.get(key)
            if isinstance(cond, (list, tuple)) and len(cond) == 2:
                op, operand = cond
                if op == "in" and value not in operand:
                    return False
                if op == "=" and value != operand:
                    return False
                if op == "<" and not (value is not None and value < operand):
                    return False
                if op == ">" and not (value is not None and value > operand):
                    return False
            elif value != cond:
                return False
        return True

    def get_all(self, doctype, filters=None, fields=None, pluck=None,
                order_by=None, limit_page_length=None, as_dict=True, **kw):
        rows = [r for r in self.tables.get(doctype, []) if self._match(r, filters)]
        if pluck:
            return [r.get(pluck) for r in rows]
        if fields and "*" not in fields:
            picked = []
            for r in rows:
                out = _DotDict()
                for f in fields:
                    alias = f
                    src = f
                    if " as " in f:
                        src, alias = [x.strip() for x in f.split(" as ")]
                    out[alias] = r.get(src)
                picked.append(out)
            rows = picked
        else:
            rows = [_DotDict(r) for r in rows]
        if limit_page_length:
            rows = rows[:limit_page_length]
        return rows

    def get_value(self, doctype, filters=None, fieldname=None, as_dict=False, **kw):
        if isinstance(filters, str):
            filters = {"name": filters}
        rows = [r for r in self.tables.get(doctype, []) if self._match(r, filters)]
        if not rows:
            return None
        row = rows[0]
        if isinstance(fieldname, (list, tuple)):
            if as_dict:
                return _DotDict({f: row.get(f) for f in fieldname})
            return [row.get(f) for f in fieldname]
        return row.get(fieldname) if fieldname else row.get("name")

    def exists(self, doctype, name):
        if isinstance(name, dict):
            return bool([r for r in self.tables.get(doctype, [])
                         if self._match(r, name)])
        return any(r.get("name") == name for r in self.tables.get(doctype, []))


def install():
    """Insert the stub into sys.modules. Returns the db handle."""
    db = _DB()
    frappe = types.ModuleType("frappe")
    frappe._db = db
    frappe.get_all = db.get_all
    frappe.get_list = db.get_all
    frappe.db = types.SimpleNamespace(
        get_value=db.get_value, exists=db.exists, get_all=db.get_all,
        get_single_value=lambda dt, f: None, set_value=lambda *a, **k: None,
        commit=lambda: None, sql=lambda *a, **k: [[0]],
    )
    frappe._dict = _DotDict
    frappe.throw = lambda msg, **kw: (_ for _ in ()).throw(Exception(msg))
    frappe.parse_json = lambda s: __import__("json").loads(s) if isinstance(s, str) else s
    frappe.get_single = lambda dt: _DotDict()
    frappe.get_cached_value = lambda *a, **k: None
    frappe.only_for = lambda *a, **k: None
    frappe.log_error = lambda *a, **k: None
    frappe.get_traceback = lambda: ""
    frappe.whitelist = lambda *a, **k: (lambda fn: fn)

    utils_mod = types.ModuleType("frappe.utils")
    utils_mod.flt = flt
    utils_mod.cint = cint
    utils_mod.nowdate = lambda: "2026-11-25"
    utils_mod.now_datetime = lambda: "2026-11-25 12:00:00"
    utils_mod.add_days = lambda d, n: d
    utils_mod.get_link_to_form = lambda dt, n: n
    frappe.utils = utils_mod

    model_mod = types.ModuleType("frappe.model")
    doc_mod = types.ModuleType("frappe.model.document")
    doc_mod.Document = type("Document", (), {})
    model_mod.document = doc_mod

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils_mod
    sys.modules["frappe.model"] = model_mod
    sys.modules["frappe.model.document"] = doc_mod
    sys.modules["frappe._"] = None
    frappe._ = lambda s: s
    return db
