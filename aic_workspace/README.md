# Workspace (Odoo 19)

> Port of Workspace 3.6 from the 20.0 branch (2026-10). Same features; the Odoo 19 differences are listed under
> *Odoo 19 notes* below. The rest of this file describes the 20.0 history.

Companion module to **Core** (`aic_theme`). It adds the interactions the pure-CSS
theme cannot do on its own. Everything is a **per-user preference** (My Preferences →
*Workspace*, or the avatar menu) and every default is stock Odoo behaviour, so
installing the module changes nothing until a user opts in.

## Quick due dates (19.0.3.9.0)
Schedule Activity (and the activity's own form) has one-tap due dates under the date field: **Today**,
**Tomorrow**, **Next week** (the first day of next week in the user's language) and **In 2 weeks**. The pick
matching the date is highlighted; the date field stays for any other day. A view widget placed by
`views/mail_activity_views.xml` (`static/src/activity/date_picks.js`).

## Records in Ctrl+K (19.0.3.8.0)
Type two letters or more in the command palette and the matching records appear under the commands: contacts and
companies, leads and opportunities, quotations and sales orders, invoices, credit notes and bills, requests for
quotation and purchase orders, transfers, tasks, tickets and products, each with its kind and a hint (the customer
and the amount, the project, the e-mail) so records with the same name can be told apart. Enter opens the record,
Ctrl+Enter opens it in a new tab.
* One call per search (`aic.search.search_records`): Odoo's own `name_search` per model, only for models the
  user may read and with their record rules, four results per model and twelve in all; apps that are not installed
  are skipped. Other modules can add their own models by extending `_aic_search_sources`.
* 19-94 ms per search on the demo database. The palette keeps its fuzzy filter; a record found through its
  customer (a credit note for "acme") stays in the list.

## Shorter kanban cards (19.0.3.7.0)
The chatter pill on a kanban card used to reserve a 40px strip at the bottom of every card. A card with a bottom
row of its own (pipelines, tasks, projects, employees) now takes the pill at the end of that row: CRM cards are
18% shorter (156 → 128px), tasks 147 → 128px, projects 198 → 168px. Cards without such a row (contacts,
products), a contact's picture column on the right, and a task whose sub-task list is open keep the strip.
Checked on desktop and phone: nothing on a card overlaps the pill.
On Odoo 19 the card's main block is a plain `<main>` (Odoo 20: `.o_record_main`); contacts have their picture on the
left there, so they shorten too.

## Confirmations close the phone action sheet (19.0.3.6.3)
On a phone a record's secondary actions sit in Odoo's bottom sheet. An action with a confirmation (Cancel on a
quotation, Reset to Draft) opened its dialog before Odoo closed the sheet, so the sheet stayed open behind the
dialog and after "No, go back" (`static/src/mobile/confirm_closes_sheet.js`). The action runs as before.

## Filter sheet and list-row swipes (20.0.3.6.0)
* **Filter sheet** (design M6): on phones Odoo's search menu shows filters and groupings as chips, the active
  ones in the "you are here" colour, favourites as rows, and a sticky *Show results* key that closes it. It is
  Odoo's own menu and search model; only the layout changes.
* **Swipe on list rows**: the same keys as on cards (Call, WhatsApp, Plan, the next step) for lists that show on
  phones (list-only screens). Only the view's own list: never the lines of a form, a dialog or sample data.
  Odoo's long press that selects rows still works.

## Swipe actions on phone cards (20.0.3.5.0)
Swipe a kanban card left on a phone: it slides aside and shows up to three keys (design M2).
* **Call** (the record's number or its contact's), **WhatsApp** (the theme's share sheet when aic_send is installed,
  else a wa.me link) and **Plan** (Odoo's Schedule Activity dialog, for models with activities).
* **The next step** when the record has one and you may write it: Confirm a quotation or a purchase order, Won for
  an opportunity, Confirm a draft invoice. It runs the same button method as the form. Other modules add their
  own by extending `aic.swipe._aic_swipe_primary()`.
* Vertical scrolling and Odoo's long-press selection are unchanged: a swipe only starts on a clearly sideways
  move. Tap the card or swipe back to close; one tray is open at a time.
* Fix: the chatter-button patch shared one object between FormController and KanbanRecord, which tied their
  `super` chains together; each patch now gets its own object.

## The installed app in the company's brand (20.0.3.4.0)
Odoo 20 can already be installed as an app (PWA), but it is always called "Odoo", with Odoo's icon and a purple
window. With the Core theme on:
* **Name** is the company name (bracketed parts dropped from the short name under the icon), unless an admin
  set Odoo's own *web.web_app_name*.
* **Icons** are the company logo centred on white: 192 and 512 px, plus a maskable 512 px icon whose logo stays
  inside the launcher's safe zone, and a 180 px icon for iOS. A company without a logo keeps Odoo's icons. The
  icon URLs carry the logo's version, so a new logo reaches installed apps.
* **Window and splash** are the theme's white ground; in dark mode the page's status bar takes the dark ground.
* **Shortcuts** (long-press on the icon): Home and Focus queue when Home is installed, then Odoo's own.
* **Offline page** shows the company icon and name and uses the action colour.
Turning the theme off gives Odoo's manifest back unchanged. Tests: `tests/test_installed_app.py`.

## Phone tabs and stage chips (20.0.3.3.0)
* **Tab bar** is now Home · *current app* · **+** · Activities · Me. Home opens the user's home action (Home
  when installed, else the app drawer); the second tab shows the open app's icon and opens its menus, or "Apps" on
  Home; **+** is the tangerine key and presses the view's own *New* button (off where the view has none);
  Activities opens the Focus queue (Home) or Odoo's activity menu, with the count as a badge; Me is the
  burger menu as before.
* **Stage chips** replace the floating stage picker on grouped kanbans: a sticky row of chips (All plus one per
  stage with its count) above the stacked stages. A chip folds the other stages and hides the empty ones; tapping
  it again, or All, brings everything back.

## Saved searches as chips (20.0.3.2.0)
The current user's favourites (saved searches) for the view appear as chips under the control panel, up to eight. A chip
applies the favourite and shows it as active in the "you are here" colour; clicking it again removes it. It follows
the search model (`getSearchItems` / `toggleSearchItem`), so the search bar, the Favourites menu and the chips always
agree.

## Features

### Split Form View
When enabled, clicking a record in a **list** or **kanban** opens its form in a panel beside
the list instead of navigating away — the Backmate/Spiffy "split view" pattern, on the theme's
design.

* The panel embeds Odoo's **own form view** (`View` component, as `FormViewDialog` does), so
  the header buttons, statusbar, sheet, tabs and chatter all behave exactly as normal.
* The list/kanban is unchanged; the selected record is highlighted.
* Panel header: record title, ‹ › to move between records, ⤢ to open the full form, ✕ to close.
* A teal edge tab collapses/​restores the list so the form can take the full width.
* Draggable divider (position remembered per browser); form on the right or below.
* Off by default → stock Odoo (records open on their own page). Never active on phones or
  inside embedded x2many lists.

### Left pane (optional)
The stock Odoo top bar always stays exactly as it is. A **☰ button** at its left shows/hides
an application pane:

* *Open, full* — apps with icons + names, the current app's sections listed under it.
* *Open, icons* — a 60 px icon rail that expands on hover.
* The pane sits under the top bar and shifts only the action area.

### v3 (2026-09-27): collapsed pane 72 px

The collapsed pane is 72 px (was 60): 12 px + the 40 px key + a gutter + the scrollbar column,
which `scrollbar-gutter: stable` reserves so the keys never move and the bar never overlaps them.
Pane icons take the theme's mono filter at rest; the hovered, open (fly-out) and active app carry
the accent. The scrollbar itself follows the theme's hover-only rule.

### Phones (below 768px)
Core keeps what Odoo does not have and restyles what it does (the theme draws Odoo's own phone UI in clay).
v2 (2026-09-27): while the shell is on screen the tab bar is the one navigator — Odoo's ☰ in the top bar is hidden
(the Apps and Menu tabs open the same drawers); tab labels are 11 px in the muted ink; the theme's bottom action bar
on record forms sits above the tab bar; the stage button no longer covers the last card's keys.
* **Tab bar** (before 3.3; see above for the current tabs) — Apps · Menu · Activity · Account at the bottom of the screen. The tabs open Odoo's OWN phone
  navigation: the app drawer with all apps (Enterprise: the home menu), the drawer with the current app's menus,
  the activity menu, and the burger menu (user, companies, preferences, *Install app*, log out — plus the theme's
  *Theme preferences*, Community's *Dark mode* and a *Developer mode* switch for phones / installed apps).
  Optionally hidden while a record's form is open (Theme preferences › Phone).
* **Stage picker** (replaced by stage chips in 3.3) — on a grouped kanban a floating key opens the list of stages (real server totals); picking one
  filters the kanban on it (a real search domain).
* **Show more** — the theme stacks kanban stages top to bottom; each shows its first four cards and a *Show more*.
* **Calendar** — previous / next keys and a tap on the period title to jump to any month.
* **Gantt** — a vertical gantt (time runs down, one column per row) instead of the sideways timeline.
* **Chatter** — a chatter key on every kanban card, list row and form opens the record's chatter in a small
  window, full screen or a bubble.
* Forms, the breadcrumb, the settings' section picker and PWA install are Odoo 20's own (restyled).

## How it is wired (no template surgery on the core views)
* `res.users` gains `aic_nav`, `aic_split`, `aic_split_side` (self-readable/writable),
  delivered to the web client in `session_info`.
* `aic_prefs` service holds the reactive preferences (+ per-browser panel width / pane state).
* The split panel is injected through **`web.Layout`** (patched), which every view — including
  app-specific list/kanban subclasses — renders through.
* The left pane is a **main_components** overlay; the ☰ button is prepended to the navbar.

## Requirements
`web`, `mail`, `aic_theme`. Odoo 19.0, Community and Enterprise (the phone gantt only where `web_gantt`
is installed).

## Odoo 20 notes
* Odoo 20 runs **OWL 3**: every component declares its props with `useProps`, keeps state in `proxy` / `signal`,
  reads refs as `signal.ref()`, and templates write `this.…` explicitly. Nothing relies on the Owl 2
  compatibility layer except `useSubEnv` / `render` from `@web/owl2/utils`, which Odoo's own views still use.
* Shared requests (does this model have a chatter? how many messages?) go through the global ORM service:
  Odoo 20 leaves the calls of a destroyed component pending for ever, and a grouped kanban builds its cards twice.
* `res.users` preference fields are `user_writeable=True` (Odoo 20 replaced `SELF_WRITEABLE_FIELDS`).
* Phones use Odoo 20's native form (outlined fields, restyled by the theme), app drawer, burger menu, breadcrumb
  and settings section picker; the 19 module's own phone form, launcher sheets and install prompt are gone.

## Odoo 19 notes (the port)
* OWL 2: state and shared stores through `useState` / `reactive` (a component reads a module-level store through
  `useState(store)` to re-render on change), `static props`, `useRef("x")` + `t-ref` read as `.el`,
  `useEffect(callback, deps)` instead of `useOnChange`, and templates without `this.`.
* Phone or desktop is `env.isSmall` (Odoo 20's `ui` service does not exist on Breadcrumbs or the kanban renderer).
  The menu service is not reactive: the left pane re-renders on `MENUS:APP-CHANGED`.
* Template hooks differ: the split view patches `t-slot='default'` of the Layout, the stage chips the kanban's
  `t-foreach="getGroupsOrRecords()"`. Floating chatter imports `@mail/chatter/web_portal/chatter`.
* Icons: Odoo 19 has no Material Symbols; `static/src/compat/icons_19.scss` draws the `<i class="oi" data-icon>`
  names used here with Font Awesome 4.7.
* `res.users` preferences use `SELF_READABLE_FIELDS` / `SELF_WRITEABLE_FIELDS` (`user_writeable` is Odoo 20 only);
  `tests/test_prefs.py` writes them as a normal user.
* Settings booleans are read with `get_param`; the installed app's icon is base64-encoded (no `BinaryBytes`).
* The phone gantt is the 19 branch's own `gantt_phone` (Odoo 19's gantt differs from 20's).
