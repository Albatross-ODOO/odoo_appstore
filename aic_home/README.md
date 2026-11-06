# Home (Odoo 20)

> Odoo 19 port of the 20.0 module (2026-10); see *Odoo 19 notes* at the end.

A role-aware start screen for the Odoo backend: what you missed, what is due today, the work that needs you, and
your apps, on one screen. Part of the Core bundle; uses the `aic_theme` colour roles, so it follows the
company palette and dark mode. Community and Enterprise.

## What it shows
- **Focus card**: greeting, date, Home role and a one-paragraph summary built from the counts (no AI service).
- **Missed**: your overdue activities, oldest first, with *Done* and *Move all to today*.
- **Today**: your meetings (calendar) and activities due today.
- **KPI tiles and panels for the Home role** (each opens the matching list or record):

| Role | Tiles | Panels |
|---|---|---|
| Sales | Hot deals, Quotations expiring, Confirmed this month, Overdue activities | Hot opportunities (no next step / late activity / gone quiet via Odoo's rotting), No next step, Quotations expiring |
| Warehouse | Receipts today, Dispatches today, Late transfers (30 days), Waiting for stock | Receipts today, Dispatches today, Late transfers, Older backlog → clean-up |
| Purchase | Delayed receipts, RFQs awaiting reply, To approve, Reorder alerts | Delayed receipts, Waiting on vendors, Reorder suggestions |
| Accounts | Overdue receivables, Bills due, Bills to post, Bank lines to reconcile | Overdue receivables (largest first), Bills due this week |
| Service | My open tasks, Due or overdue, My open tickets | My tasks: due and overdue, Tickets waiting on me |
| Owner | Sales this month, Open pipeline, Overdue receivables, Late transfers | Overdue receivables, Late transfers, Hot opportunities (all) |

- **Your apps**, ordered for the role, with badges counting what needs you.

Blocks are built only when their app is installed (`model in env`) and always as the user, so record rules and
access rights apply; a block the user cannot read is skipped, never an error.

## My week (19.0.1.5.0)
The top card of Home switches between **Today** and **My week**. My week shows:
* Activities you completed each day of the week (Odoo's "done" message, authored by whoever marked it done)
  against the ones due that day and still open, the totals (done, still due before the week ends, overdue)
  and last week's count next to this week's.
* **Work moved**: what you got through in the installed apps this week, with last week beside it, ordered for
  your role (opportunities won, orders confirmed, quotations created, transfers done, purchase orders
  confirmed, invoices posted, tasks and tickets closed). Each opens the list.
* **Your team**, for the leader of a sales team or the manager of employees (Employees app): each person's
  overdue, still due this week and done this week. Alphabetical and never ranked: it is there to see who needs a
  hand. Only counts are read for colleagues.
The week starts on the language's first day of the week. About 100 ms per visit at 15,000 opportunities.

## Failed to send (19.0.1.4.0)
A panel at the top of Home, for every role, when one of your own sends did not go out in the last 30 days:
e-mails and text messages Odoo marks failed or bounced, and WhatsApp messages in error when the WhatsApp app
is installed. One row per document (the record, the channel and recipient, the reason, how long ago); a row
opens the document, where the chatter shows the failed recipients. Only documents you may read.
* **Retry** puts the failed e-mails back in the outgoing queue (the address is read again when it goes, so a
  corrected contact is used) and resends failed WhatsApp messages. Bounces and missing addresses are left: they
  need the contact corrected first.
* **Dismiss** is Odoo's own dismiss of the messaging menu for e-mail and text messages; WhatsApp messages are
  not changed, Home only stops showing those failed until then.
* The summary sentence counts them. Measured with 500 failed sends on 500 documents: 16 ms.

## Focus queue (20.0.1.1.0)
*Home → Start my queue* (or `/odoo/focus`): your activities due today or earlier, oldest first, one record at a
time, on any model with activities (leads, tasks, tickets, orders, contacts, personal to-dos).
- The card shows the activity and its note, the record with its contact (call, WhatsApp, email links), a few facts
  for known models (lead: expected revenue, probability, stage, tags; order, task, ticket, invoice, purchase), the
  latest messages, and how many other activities the record has.
- A note box: what you type is logged on the record when you mark the activity done.
- Keys: **D** done · **F** done and follow up in 2 days (same type) · **P** done and plan next (Odoo's dialog) ·
  **S** tomorrow · **W** next week · **→** skip · **←** back · **O** open the record · **Ctrl/⌘+Enter** in the note = done.
- Progress: done today against what is still due; filters by type of record.
- Server: `aic.focus` (`get_queue`, `get_card`, `mark_done`, `snooze`, `done_and_plan`), always as the user; you can
  only act on your own activities.

## Home role
*Settings → Users → a user → Preferences → Home role*: Sales, Warehouse, Purchase, Accounts, Service, Owner, or
**Suggest from activity** (default), which picks the role from what the person created or owns in the last 90
days, then from their manager groups. The role never changes access rights.

## Start screen
`ir.http.session_info` sets `home_action_id` to Home for internal users who have no home action of their own; the
web client already falls back to it when the URL names no action (Community and Enterprise, no JS patch). Turn it
off in *Settings → Backend theme → Start on Home*. Home is also an app tile in the app menu.

## Backlog clean-up
Managers see an *Old quotations* / *Older backlog* panel when old records pile up. The wizard lists what matches
(quotations older than N days still in draft/sent; deliveries or receipts more than N days late), then cancels them
or moves transfers to a new date. Sales managers can clean quotations, inventory managers transfers; the user must
tick a confirmation box.

## Performance
One RPC per visit (`aic.home.get_home_data`): counts and the top five rows per panel. Nothing runs on other screens.

## Tests
`tests/test_home.py`: every role as an administrator and as a user with almost no rights, Missed + reschedule,
the suggested role, the clean-up wizard (rights, preview, reschedule), and the start screen (own home action wins,
setting turns it off).

## Languages (20.0.1.3.0)
French, Spanish, German and Arabic. Every sentence with a value in it is one translatable string with a
placeholder (no fragments glued together), the role label comes from the field's translated selection, and the
date on the greeting card uses the language's own full format.

## Performance (20.0.1.1.2)
Measured on a copy of the Enterprise demo database grown to 15,000 opportunities, 30,000 contacts, 8,000
quotations, 2,500 transfers, 2,000 posted invoices and 4,000 activities: one Home call takes 95-240 ms for any
role, with 33-61 queries whatever the data size (no query per record). Totals (hot deals, confirmed this month,
to approve, overdue receivables, open pipeline) are single aggregate queries; before, the owner Home summed every
open opportunity in Python and took up to 440 ms. The Focus queue loads in under 50 ms with 2,375 due activities.

## Customise home (20.0.1.2.0)
*Customise* on the greeting card opens a sheet (a centred card on the desktop, a bottom sheet on phones) where
each person decides what their Home shows: a switch per tile, panel and section (Missed, Today, Your apps), and up /
down keys to order tiles and panels. The choice is saved for the person's current role (`res.users.aic_home_layout`,
written only through `aic.home.save_layout` / `reset_layout` for the current user); *Reset* goes back to the
role's own layout. A hidden panel that is empty today keeps its choice for the day it comes back. Keyboard: the
sheet takes focus, Escape closes it and focus returns to *Customise*.


## Odoo 19 notes (the port)
- Access rights in `security/ir.model.access.csv` (Odoo 20: `ir.access.csv`); settings read with `get_param`.
- Components use `useState` and `static props` (OWL 2), `standardActionServiceProps` from
  `@web/webclient/actions/action_service`; icons are Font Awesome (activity types carry `fa-*` classes in 19);
  app icons read `webIcon.iconClass`.
- Checked on fresh Odoo 19 Community and Enterprise demo databases: tests pass, Home is the start screen,
  Focus, Customise and Share on WhatsApp work on desktop and phone with no errors.
