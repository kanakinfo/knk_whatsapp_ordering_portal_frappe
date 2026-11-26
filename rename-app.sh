#!/usr/bin/env bash
# Align the Python package name with the Frappe app name.
#
# Frappe requires app name == python package folder == folder in apps/.
# This repo was scaffolded as knk_whatsapp_ordering_portal_frappe but carries
# a package folder called wa_order, so flit cannot find the module.
#
# Leaves alone, deliberately:
#   - the INNER wa_order/ directory: that is the module dir for module
#     "WA Order", named from the module, not the app
#   - the custom fieldnames wa_order_section and wa_order_ref: those are
#     database columns, and renaming them would break the Sales Order link
#
# Run from the repo root, then commit and push.
set -euo pipefail

APP=knk_whatsapp_ordering_portal_frappe

[ -d wa_order ] || { echo "No wa_order/ here — already renamed?"; exit 1; }
[ -f pyproject.toml ] || { echo "Run this from the repo root."; exit 1; }

echo "1. moving the package folder"
if git rev-parse --git-dir >/dev/null 2>&1; then
  git mv wa_order "$APP"
else
  mv wa_order "$APP"
fi

echo "2. rewriting module imports (not the fieldnames)"
grep -rl 'from wa_order\.' "$APP" tests 2>/dev/null \
  | xargs -r perl -pi -e "s/\bfrom wa_order\./from ${APP}./g"

echo "3. rewriting hooks.py"
perl -pi -e "
  s/^app_name = \"wa_order\"/app_name = \"${APP}\"/;
  s/\"wa_order\.install\./\"${APP}.install./g;
  s/\"wa_order\.api\./\"${APP}.api./g;
  s|/assets/wa_order/|/assets/${APP}/|g;
  s/\"name\": \"wa_order\"/\"name\": \"${APP}\"/;
" "$APP/hooks.py"

echo "4. rewriting bench-command docs and the validator path"
perl -pi -e "s/\bwa_order\.demo\./${APP}.demo./g" "$APP/demo.py"
perl -pi -e "s|ROOT / \"wa_order\"|ROOT / \"${APP}\"|" tests/validate_doctypes.py
perl -pi -e "s/\bwa_order\.utils\b/${APP}.utils/g" tests/stub_frappe.py
perl -pi -e "s/recursive-(include|exclude) wa_order/recursive-\$1 ${APP}/" MANIFEST.in

echo "5. removing the competing build config"
# pyproject.toml (flit) is authoritative; setup.py declared name=wa_order and
# having both is what made this confusing.
rm -f setup.py
rm -f .DS_Store

cat > .gitignore <<'EOF'
*.pyc
__pycache__/
.DS_Store
*.egg-info
node_modules/
.venv/
.pytest_cache/
EOF

echo
echo "Done. Check it:"
echo "  python3 tests/validate_doctypes.py"
echo "  python3 -m pytest tests/ -q"
echo "  grep -n 'wa_order' ${APP}/hooks.py   # should show nothing"
