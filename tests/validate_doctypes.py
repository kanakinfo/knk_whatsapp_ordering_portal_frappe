#!/usr/bin/env python3
"""Validate DocType JSON against Frappe v15 rules without needing a bench.

Catches the structural mistakes that otherwise surface as a failed
`bench migrate` on a live site.

    python3 tests/validate_doctypes.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "wa_order"

# Fieldnames Frappe reserves on every document.
RESERVED = {
    "name", "owner", "creation", "modified", "modified_by", "docstatus",
    "idx", "parent", "parentfield", "parenttype", "doctype", "_user_tags",
    "_comments", "_assign", "_liked_by", "file_list",
}

NO_OPTIONS_NEEDED = {
    "Section Break", "Column Break", "Tab Break", "Data", "Int", "Float",
    "Check", "Text", "Small Text", "Long Text", "Text Editor", "Date",
    "Datetime", "Time", "Percent", "Password", "Attach", "Attach Image",
    "HTML", "Button", "Code", "Markdown Editor", "Duration", "JSON",
    "Phone", "Rating", "Signature", "Color", "Barcode", "Geolocation",
    "Heading", "Image", "Read Only", "Autocomplete", "Icon",
}
NEEDS_OPTIONS = {"Link", "Table", "Table MultiSelect", "Select", "Dynamic Link"}
LAYOUT = {"Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button"}

# ERPNext/Frappe doctypes we legitimately link to.
KNOWN_EXTERNAL = {
    "Item", "Customer", "Sales Order", "Company", "Price List", "Warehouse",
    "UOM", "Currency", "Brand", "Item Group", "Territory", "Customer Group",
}

REQUIRED_TOP = ["doctype", "name", "module", "fields", "field_order",
                "creation", "modified", "owner", "modified_by", "engine",
                "permissions", "links", "actions"]

errors: list[str] = []
warnings: list[str] = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def load_all():
    docs = {}
    for path in sorted(APP.rglob("doctype/*/*.json")):
        if path.stem != path.parent.name:
            continue
        try:
            docs[path] = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            err(path.name, f"invalid JSON - {exc}")
    return docs


def validate(path, doc, local_names):
    where = doc.get("name", path.name)

    for key in REQUIRED_TOP:
        if key not in doc:
            err(where, f"missing top-level key '{key}'")

    if doc.get("doctype") != "DocType":
        err(where, "top-level 'doctype' must be 'DocType'")

    # The folder name must be the snake_case of the doctype name, or Frappe
    # will not find the controller module.
    expected_slug = re.sub(r"[^a-z0-9]+", "_", doc.get("name", "").lower()).strip("_")
    if path.parent.name != expected_slug:
        err(where, f"folder '{path.parent.name}' should be '{expected_slug}'")

    fields = doc.get("fields", [])
    order = doc.get("field_order", [])
    names = [f.get("fieldname") for f in fields]

    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        err(where, f"duplicate fieldnames: {sorted(dupes)}")

    if set(order) != set(names):
        missing = set(names) - set(order)
        extra = set(order) - set(names)
        if missing:
            err(where, f"field_order missing: {sorted(missing)}")
        if extra:
            err(where, f"field_order references unknown: {sorted(extra)}")

    is_table = bool(doc.get("istable"))
    is_single = bool(doc.get("issingle"))

    if not is_table and not is_single and not doc.get("permissions"):
        err(where, "non-child doctype has no permissions")
    if is_table and doc.get("permissions"):
        warn(where, "child table defines permissions (ignored by Frappe)")

    if not is_table and not is_single:
        if not doc.get("autoname") and not doc.get("naming_rule"):
            warn(where, "no autoname/naming_rule; Frappe will prompt for names")
        if doc.get("autoname") == "naming_series:" and "naming_series" not in names:
            err(where, "autoname is 'naming_series:' but no naming_series field")

    title = doc.get("title_field")
    if title and title not in names:
        err(where, f"title_field '{title}' is not a field")

    for sf in (doc.get("search_fields") or "").split(","):
        sf = sf.strip()
        if sf and sf not in names:
            err(where, f"search_fields references unknown field '{sf}'")

    for field in fields:
        fname = field.get("fieldname")
        ftype = field.get("fieldtype")
        fw = f"{where}.{fname}"

        if not fname:
            err(where, f"field without a fieldname: {field}")
            continue
        if not ftype:
            err(fw, "field without a fieldtype")
            continue
        if fname in RESERVED:
            err(fw, f"'{fname}' is a reserved Frappe fieldname")
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", fname):
            err(fw, f"fieldname '{fname}' must be snake_case")
        if ftype not in NO_OPTIONS_NEEDED and ftype not in NEEDS_OPTIONS \
                and ftype not in {"Currency", "Date Range", "Small Text"}:
            warn(fw, f"unusual fieldtype '{ftype}'")

        if ftype in NEEDS_OPTIONS and not field.get("options"):
            err(fw, f"{ftype} field needs 'options'")

        if ftype in {"Link", "Table", "Table MultiSelect"}:
            target = (field.get("options") or "").strip()
            if target and target not in local_names and target not in KNOWN_EXTERNAL:
                warn(fw, f"links to '{target}' which is not in this app "
                         f"(fine if ERPNext provides it)")

        if ftype == "Table" and field.get("options") in local_names:
            if not local_names[field["options"]].get("istable"):
                err(fw, f"Table points to '{field['options']}' which is not istable")

        if ftype not in LAYOUT and not field.get("label"):
            warn(fw, "no label")

        if field.get("reqd") and field.get("hidden") and not field.get("default"):
            err(fw, "field is both required and hidden with no default")

        if field.get("reqd") and ftype in LAYOUT:
            err(fw, f"{ftype} cannot be 'reqd'")

        fetch = field.get("fetch_from")
        if fetch:
            src = fetch.split(".")[0]
            if src not in names:
                err(fw, f"fetch_from references unknown field '{src}'")

        dep = field.get("depends_on") or ""
        if dep and not dep.startswith("eval:"):
            if dep not in names:
                warn(fw, f"depends_on '{dep}' is not a field "
                         f"(use eval: for expressions)")

        if ftype == "Select":
            opts = [o for o in (field.get("options") or "").split("\n") if o != ""]
            default = field.get("default")
            if default and default not in opts:
                err(fw, f"default '{default}' is not among the Select options")

        if ftype == "Currency" and field.get("options"):
            if field["options"] not in names:
                err(fw, f"Currency options '{field['options']}' must name a "
                        f"Currency field on this doctype")

    return where


def validate_workspace():
    for path in sorted(APP.rglob("workspace/*/*.json")):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            err(path.name, f"invalid JSON - {exc}")
            continue
        where = f"workspace {doc.get('name', path.name)}"
        if doc.get("doctype") != "Workspace":
            err(where, "doctype must be 'Workspace'")
        content = doc.get("content")
        if isinstance(content, str):
            try:
                blocks = json.loads(content)
            except json.JSONDecodeError as exc:
                err(where, f"content is not valid JSON - {exc}")
                return
            shortcut_labels = {s.get("label") for s in doc.get("shortcuts", [])}
            card_labels = {l.get("label") for l in doc.get("links", [])
                           if l.get("type") == "Card Break"}
            for b in blocks:
                if b.get("type") == "shortcut":
                    label = b["data"].get("shortcut_name")
                    if label not in shortcut_labels:
                        err(where, f"content references shortcut '{label}' "
                                   f"which is not defined")
                if b.get("type") == "card":
                    label = b["data"].get("card_name")
                    if label not in card_labels:
                        err(where, f"content references card '{label}' which "
                                   f"has no Card Break link")
        else:
            err(where, "content must be a JSON string")


def validate_module_files():
    # modules.txt is one module name per line; names may contain spaces.
    modules = [m.strip() for m in (APP / "modules.txt").read_text().splitlines()
               if m.strip()]
    for path in sorted(APP.rglob("doctype/*/*.json")):
        if path.stem != path.parent.name:
            continue
        doc = json.loads(path.read_text())
        if doc.get("module") not in modules:
            err(doc.get("name"), f"module '{doc.get('module')}' is not in "
                                 f"modules.txt {modules}")
        # Every non-child doctype needs a controller .py next to the JSON.
        py = path.with_suffix(".py")
        if not py.exists():
            err(doc.get("name"), f"missing controller {py.name}")
        init = path.parent / "__init__.py"
        if not init.exists():
            err(doc.get("name"), "missing __init__.py in doctype folder")


def main():
    docs = load_all()
    local_names = {d.get("name"): d for d in docs.values()}
    print(f"Validating {len(docs)} doctypes in {APP}\n")
    for path, doc in docs.items():
        name = validate(path, doc, local_names)
        print(f"  checked {name}")
    validate_workspace()
    validate_module_files()

    print()
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ! {w}")
        print()
    if errors:
        print(f"{len(errors)} ERROR(S):")
        for e in errors:
            print(f"  x {e}")
        return 1
    print("No errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
