# wa_order — WhatsApp order capture inside ERPNext

A Frappe app that puts the WhatsApp order review queue **inside ERPNext**.
The parsing agent runs beside it; ERPNext holds the master data, makes the
auto-post decision, and creates the Sales Order.

```
dealer's WhatsApp  →  agent (parse + match)  →  ERPNext
                                                 ├── WhatsApp Order (queue)
                                                 └── Sales Order
```

**Why the queue moved here:** the client sees one system. Thresholds live in
WhatsApp Order Settings, so tuning behaviour is a setting change rather than a
redeploy. Credit limits and stock are checked against live data at the moment
of posting, not against a copy the agent fetched earlier.

---

## 0. Versions

Runs on **Frappe/ERPNext v15 and v16**. Written against the v15 DocType schema
and made v16-compatible. v14 is untested but should work; **v13 and older will
not** — the workspace format differs. Check yours with `bench version`.

v16 needs Python 3.14+ and Node 24+. Three v16 changes are already handled:
`sort_field` is set to `creation` on every doctype, `hooks.py` carries an
`add_to_apps_screen` entry (v15 ignores hooks it doesn't know), and
`has_app_permission` returns a real boolean because v16 no longer accepts a
truthy value.

One thing to check on v16: the apps-screen icon routes to `/app/whatsapp-orders`.
If your build has moved the desk to `/desk` and the icon 404s, change that one
string in `hooks.py`. It affects the icon only.

## 1. Install

```bash
cd ~/frappe-bench
bench get-app wa_order /path/to/wa_order
bench --site yoursite.local install-app wa_order
bench --site yoursite.local migrate
bench restart
```

The install adds, and `bench migrate` keeps up to date:

| Where | What |
|---|---|
| Item | **Dealer Aliases** table, *Exclude from WhatsApp ordering* |
| Customer | **Additional WhatsApp Numbers**, **Shop Name Aliases** |
| Sales Order | **WhatsApp Order** link, for traceability both ways |

New doctypes: WhatsApp Order, WhatsApp Order Item, WhatsApp Order Issue,
Item Dealer Alias, WhatsApp Order Settings. A **WhatsApp Orders** workspace
appears in the sidebar.

To remove it cleanly: `bench --site yoursite.local uninstall-app wa_order`
(the `before_uninstall` hook drops the custom fields).

---

## 2. Configure

Open **WhatsApp Order Settings**:

| Field | Set it to |
|---|---|
| Company, Selling Price List, Warehouse | your demo company's values |
| **Submit Sales Order** | **off** — orders land as drafts. Leave it off for a pilot. |
| Auto-post Confidence | `0.82` to start. Raise it to send more to review. |
| Block on Credit Limit | on |
| Block on Insufficient Stock | off at first — it blocks a lot on a half-stocked demo site |
| Agent URL / Agent Shared Token | the agent service, so ERPNext can send the reply when an operator approves |

---

## 3. Load demo data (fresh site only)

```bash
bench --site yoursite.local execute wa_order.demo.install
```

Creates 37 items with dealer aliases and case conversions, 8 customers with
WhatsApp numbers and credit limits, opening stock, and opening receivables so
the credit-limit block is real rather than staged. Safe to re-run.

If opening stock or receivables fail (common on a site with no chart of
accounts set up), the command says so and carries on — everything else still
works. Remove it all with `wa_order.demo.uninstall`.

**Put your own phone number on a demo customer** so you can message from it:

```
Customer → Sharma General Store → Mobile No, or Additional WhatsApp Numbers
```

---

## 4. Connect the agent

In the agent's `.env`:

```bash
ERPNEXT_URL=https://erp.yourhost.com
ERPNEXT_API_KEY=...          # ERPNext: User → API Access → Generate Keys
ERPNEXT_API_SECRET=...
ERPNEXT_WA_ORDER_APP=true    # the switch that hands the queue to ERPNext
AGENT_TOKEN=pick-a-shared-secret   # same value as Agent Shared Token above
```

Give the API user the **Sales User** role. That is enough: the endpoints call
`frappe.only_for(("Sales User", "Sales Manager", "System Manager"))`.

With `ERPNEXT_WA_ORDER_APP=true` the agent stops deciding anything. It parses,
matches against aliases pulled live from ERPNext, and calls
`wa_order.api.ingest`. ERPNext does the rest.

Check the wiring:

```bash
curl -s -u KEY:SECRET \
  "https://erp.yourhost.com/api/method/wa_order.api.catalogue" | head -c 400
```

---

## 5. Connect the real WhatsApp Business API

You have the API, so this is the part that makes the demo land. Five things,
and two of them bite people.

**a. Get a permanent token.** The token shown on Meta's *API Setup* page
expires in 24 hours. A demo booked for tomorrow will fail with a token you
generated today. Create a **System User** in Business Settings, assign it to
the WhatsApp app with `whatsapp_business_messaging` and
`whatsapp_business_management`, and generate a token with **no expiry**.

**b. Point the webhook at the agent.** Needs public HTTPS:

```bash
cloudflared tunnel --url http://localhost:8000     # or ngrok http 8000
```

In Meta → WhatsApp → Configuration → Webhook:
- Callback URL: `https://<your-tunnel>/webhook/whatsapp`
- Verify token: the same string as `WHATSAPP_VERIFY_TOKEN` in the agent's `.env`
- Click **Verify and save**, then **subscribe to `messages`**

Forgetting the `messages` subscription is the single most common reason
"nothing happens" — the webhook verifies fine and then never fires.

**c. Set the agent's credentials:**

```bash
WHATSAPP_TOKEN=<permanent system user token>
WHATSAPP_PHONE_NUMBER_ID=<from API Setup, not the phone number itself>
WHATSAPP_VERIFY_TOKEN=<same string you typed into Meta>
```

**d. Know the 24-hour window.** You may only send free-form replies within 24
hours of that person's last message to you. The demo flow is dealer-first, so
replies work. But if you want to message a dealer who hasn't written in a day,
that must be an approved **template** message. Don't let a client discover this
in front of you.

**e. If you're on a test number**, you can only message up to 5 recipients that
you've pre-registered in the dashboard. Add the phones you'll demo from, or
move to a verified business number first.

---

## 6. The demo

Roughly eight minutes. The order matters.

1. **Open the WhatsApp Orders workspace.** Empty queue. Say what they're about
   to see: a dealer's message becoming an order with no one typing it.

2. **Send from a real phone**, from a number on a demo customer:
   ```
   5 case sunfield glucose 100g
   2 peti amrit mango 200ml
   10 packet marie
   ```
   Refresh the queue. A WhatsApp Order appears, status **Auto Posted**, Sales
   Order already created. The phone gets the confirmation back.

   Open the order and point at one line: `5 case → 240 Packet (×48)`. **This is
   the moment that sells it.** Dealers order in cases and petis; ERPNext stores
   packets; nobody had to do that arithmetic.

3. **Send something ambiguous:**
   ```
   3 case chips
   5 case sunfield glucose
   ```
   It lands in **Needs Review**, not posted. The agent could have guessed —
   there are two chips variants and two glucose pack sizes — and it refused.
   Say plainly: *one wrong auto-posted order costs more than fifty reviewed
   ones.*

4. **Fix it in front of them.** Change the item on the line, save, Approve.
   Watch the quantity recompute: switch the 100g SKU to 250g and 240 becomes
   120, because that case is 24 not 48. Sales Order created, dealer notified.

5. **Send the credit-limit order** from Verma Kirana's number:
   ```
   20 case refined oil
   10 case basmati rice 5kg
   ```
   Blocked, with the arithmetic shown. This is the one a finance person
   remembers.

6. **Close on the Sales Order.** Open it, show `po_no` and the WhatsApp Order
   link. Every order traces back to the message that created it.

Have a backup. Phone signal in a client's office is a real risk — keep the
agent's own simulator open on `localhost:8000` as a fallback that needs no
network.

---

## 7. Teaching it your client's vocabulary

This is where accuracy comes from, and it is now a business-user job rather
than a developer one.

**Item → Dealer Aliases** — every name dealers actually type: vernacular
(`doodh`, `tel`, `chai patti`), shorthand (`ref oil`), misspellings
(`sunfeild`). There's an **Add Dealer Alias** button on the Item form.

**Customer → Shop Name Aliases** — `sharma store`, `sharma ji`.
**Customer → Additional WhatsApp Numbers** — the owner's phone *and* the
manager's, one per line.

**Item → UOMs** — the case/peti/dozen factors. The app expands synonyms, so
defining `Case` once covers `cs`, `ctn`, `peti`, `carton` and `box`.

The fastest way to build this for a new client: export six months of their
order history, run it through the agent, and work the review queue. Two days
takes a client from roughly 70% auto-post to above 90%.

---

## 8. When something goes wrong

| Symptom | Cause |
|---|---|
| Webhook verifies, nothing arrives | `messages` field not subscribed in Meta |
| Worked yesterday, dead today | 24-hour token; switch to a System User token |
| `AuthenticationError` from the agent | API key/secret wrong, or user lacks Sales User |
| Everything lands in Needs Review | aliases missing — check the match note on each line |
| Order posts but with odd quantities | UOM conversion missing on the Item |
| Reply never reaches the dealer | outside the 24-hour window, or Agent URL not set |
| `bench migrate` fails after an edit | run `python3 tests/validate_doctypes.py` |

Agent-side log: `bench --site yoursite.local console` then check
**Error Log** for `WhatsApp Order ... failed`.

---

## 9. Testing without a bench

```bash
python3 tests/validate_doctypes.py        # schema check; run before every migrate
python3 -m pytest tests/test_utils.py -v  # UOM and pricing logic, 31 tests
```

`tests/stub_frappe.py` is a small in-memory `frappe`, so the matching and
pricing logic can be tested in seconds without a site. The agent repo has a
fake ERPNext (`tests/fake_erpnext.py`) that speaks this app's API contract, so
both sides of the wire are covered.

**If you change `api.catalogue()` or `api.ingest()`, change the fake too** —
it is the only thing holding the contract.

---

## 10. Layout

```
wa_order/
  hooks.py          app wiring, scheduler, doctype_js
  install.py        custom fields, default settings, number cards
  api.py            catalogue() and ingest() — the agent's two endpoints
  utils.py          UOM synonyms, pricing, phone normalisation
  demo.py           bench execute wa_order.demo.install
  wa_order/doctype/ WhatsApp Order + children + Settings
  wa_order/workspace/
  public/js/item.js Add Dealer Alias button
tests/
  validate_doctypes.py   schema linter (no bench needed)
  stub_frappe.py         in-memory frappe for unit tests
  test_utils.py
```
