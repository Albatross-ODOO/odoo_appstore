# Backend Theme Engine (Odoo 20)

A calm, white restyling of the Odoo 20 backend: white panels on a white ground, separated by soft layered
shadows, with seated wells for inputs. One action colour, one "you are here" highlight and one ink, per
company: the theme's own (tangerine, butter, plum), taken from the company logo, or picked by hand. Every colour is
adjusted until its text passes WCAG AA in light and dark mode. Community and Enterprise, light and dark.

## What's new in engine 1.2.0 (2026-10-15)

- **SVG logos give a palette.** "From the company logo" read only bitmaps (Pillow cannot open SVG), so a company
  with an SVG logo got no colours. The engine now reads the SVG itself: each filled shape counts with its area,
  fills inherited from groups, `<defs>`/masks/gradients skipped; a bitmap wrapped in the SVG is the fallback.
  Upgrading recomputes the logo colours of every company (an `end-` migration, so the look's own CSS is used).
- **Sign-in pages install next to Website.** Website replaces the sign-in page's `web.frontend_layout` call with
  `website.layout`; the engine's sign-in view now matches either call (before, it failed to install on a database
  with Website).

## What's new in 4.0 (2026-10)
- **White layers instead of clay.** Ground and panels are white; depth comes from a contact shadow, a soft cast
  straight down and a 1 px edge (`--nm-raised*`). Seated objects (inputs, search, kanban columns, chatter) sit in
  a tinted well ground (`--nm-well-bg`): the `nm-inset` / `nm-well` mixins now set it.
- **Colour roles.** `--nm-brand` is the primary fill (tangerine, dark ink), `--nm-action` the text-safe accent
  (links, active labels, focus), `--nm-current` the butter "you are here" (the current status-bar stage),
  `--nm-active-tint` its soft form (selected rows), `--nm-ink` / `--nm-plum` headings and the strong surface.
- **Company colours.** *Settings → General Settings → Backend theme → Theme colours*: House colours, from the
  company logo, or custom, with a live contrast preview. `models/palette.py` finds the logo's main colours
  (Pillow), gives each a role and corrects it for contrast; `res.company` stores the result as two small CSS
  blocks (light, dark), and `ir.http` puts the current one in the page head. A company on the House colours gets
  nothing extra; nothing is ever recompiled.
- **Dark mode** is a warm plum-black with the same roles lifted; Community dark keeps its own variables.
- Radii are rounder (10 / 14 / 22 px). Titles take the ink colour.
- Tests: `tests/test_palette.py` checks that every role reaches 4.5:1 for a set of sample logos and custom
  colours, in both schemes.

## What's new in 4.12 (2026-10)
- **Activity view**: Odoo filled every cell with its state colour, so a grid of overdue activities read as one pink
  alarm. Cells are a light tint of the state with a bar in its colour, the summary in the ink and the deadline in
  the state's ink (amber darker, to pass AA).
- **Schedule Activity on touch screens**: the due date showed two calendar icons (the row's and the date field's
  touch icon); a row that leads with its own icon keeps only that one. Date fields elsewhere keep theirs.

## What's new in 4.11 (2026-10)
- **Command palette (Ctrl+K)**: the search line is the palette's header (magnifier first, a large borderless field,
  the "/" or "@" mode in the action colour, an action-colour line while typing) instead of a hard tangerine box
  inside the rounded sheet. Shortcuts are small flat keys in the muted ink, hidden on touch screens where they
  mean nothing. The highlighted row is the well tint with a bar in the action colour.
- The "@" mode's actions (Create Channel, View hidden conversations) used Odoo's teal, 3.6:1: now the action
  colour (AA). The palette is in the accessibility audit, light and dark, desktop and phone.

## What's new in 4.10 (2026-10)
- **Chatter "@" suggestions**: typing @ in the composer opened the list of people *behind* the Planned Activities
  card, and once in front it was see-through (the panel makes its inner containers transparent for its relief).
  The list now floats above the chatter on a solid sheet.
- **Chatter keys**: Send message, Log note, WhatsApp and Activity did not fit the chatter column, and Activity ran
  past its edge. The keys flow into the top bar, which wraps: what does not fit goes beside the search,
  attachment and follower icons. Checked in English and French, on desktop and in the phone chatter window.

## What's new in 4.9 (2026-10)
- **Smart buttons in the control panel** (a product's On Hand, Forecasted, Sold, Purchased, Min / Max…): Odoo
  decides how many show before *More* for buttons laid edge to edge; the theme's raised ones have a gap, so the row ran
  under the pager. They now share the room: each may shrink to a few letters (the words end in an ellipsis, the
  figures never shrink) and the row stops before the pager, at every width.
- **Inventory Overview**: the operation-type cards' bar graph is shorter (96 px), and "Late 9", "Waiting 12" sit
  together at the card's right edge with the count in bold (Odoo spread them over a grid).

## What's new in 4.8 (2026-10)
- **Invoices and bills.** The payment status (Paid, In Payment, Partial, Reversed…) is a soft pill in the sheet's
  corner instead of Odoo's diagonal ribbon. The outstanding credits under an invoice's totals are a light card
  (document and amount, then date and an *Add* key) instead of a second plum panel that overflowed its column.
- **One main action per record.** When Odoo marks several header keys primary (Send *and* Print on an invoice),
  only the first keeps the brand colour.
- **Dialogs on phones are bottom sheets**: confirmations and form dialogs (register payment, schedule activity…)
  rise from the bottom edge, as tall as their content, keys under the thumb. Record pickers stay full screen.
- An overdue date in a form field is drawn at AA in its input well.

## What's new in 4.7 (2026-10)
- **Accessibility audit** (axe-core, WCAG 2.1 AA; `docs/theme_slate/accessibility.md`): with Core on, no screen
  has a contrast failure in light or dark, and nothing fails only because of Core.
- Bootstrap's grey hint text (4.3:1) takes the theme's muted ink; Community's solid status badges (white on green
  or teal, about 3:1) become the soft pills Enterprise shows.

## What's new in 4.6.2 (2026-10)
- Phone list cards keep the swipe tray (the rules that hide extra cells on a card skip it).
- **Browser smoke test** (`tests/test_assets.py`, `TestWebClientStarts`): the backend must start with no
  JavaScript error at desktop and phone size. It needs Python's `websocket-client` (Odoo skips browser tests
  without it).

## What's new in 4.6 (2026-10)
- **A test that compiles the light and dark style bundles** (`tests/test_assets.py`): libsass rejects some
  modern CSS and Odoo then silently falls back to the previous styles; the test fails instead.
- **Bottom sheets** (design M5): Odoo 20's phone dropdowns, selections and pickers open as sheets with a 30 px
  top, a slim handle, the plum-tinted scrim, 56 px rows and the current choice in butter.

## What's new in 4.5 (2026-10)
- **Keyboard focus everywhere**: notebook tabs, link buttons (Add a line, Catalog…) and required fields now show
  the focus ring. Checked by pressing Tab through Home, Focus, a list, a form and a kanban: every stop is visible.
- **Right-to-left**: checked in Arabic on desktop and phone (Home, form, pipeline, Focus, the dock and tab bar):
  the layout mirrors with no sideways scroll. Odoo needs `rtlcss` on the server for right-to-left styles.
- Reduced motion: no transition or animation is left running when the system asks for less motion.

## What's new in 4.4 (2026-10)
- **Phone thumb dock**: on phones a record's action bar floats above the tab bar as a plum dock with rounded
  corners. The main action is the brand key, other actions are light text, and the stage folds into one pill in
  the "you are here" colour.

## What's new in 4.3 (2026-10)
- **Lists**: hovering and the keyboard-focused row are neutral (the well tint); a selected row is the soft
  "you are here" tint with a bar on its edge, a little deeper under the mouse. Before, hover used the highlight
  tint and focus Odoo's teal, so selection and hover looked alike.
- **Group headers** are one continuous band (no per-cell wells), the group name keeps its case in the ink colour,
  the record count is a chip and aggregates are bold. Column headers stay uppercase.
- **"N selected"** in the control panel is the butter key.

## What's new in 4.2 (2026-10)
- **Totals panel**: the totals of orders, invoices, bills and purchase orders sit in the plum panel of design G,
  with the grand total in the display face and the "you are here" colour on its label.
- **Record titles** use the display face (Bricolage Grotesque) on every form, with a light underline instead of
  the heavy "required" bar.
- The "no next step" ring only shows in columns followed by another open column, so the closing stage (Won,
  Done…) stays quiet.

## What's new in 4.1 (2026-10)
- **Pipeline cues** on every kanban that shows activities: a record with no activity planned gets a dashed ring
  on its activity icon in the action colour ("no next step"); Odoo 20's rotting badge becomes a readable warning
  pill with an hourglass ("gone quiet"); a dragged card lifts, tilts slightly and carries an accent ring.

## Install
1. Copy `aic_theme` into your addons path.
2. Update the apps list and install **Backend Theme Engine**.
3. Reload the browser. Done.

Disable/enable without uninstalling: *Settings → General Settings → Backend theme → Backend Theme Engine*
(stored in `ir.config_parameter` key `aic_theme.enabled`; reload the page after changing).

## How it works (performance-oriented)
| Piece | What it does | Cost |
|---|---|---|
| `static/src/scss/tokens.scss` | Derives all theme tokens (surfaces, shadows, accents, radii) from Odoo SCSS variables and exposes them as CSS custom properties on `.o_aic_theme`. Because `web.assets_web_dark` recompiles the backend bundle with the dark variables, the same file produces the dark palette. | compile‑time only |
| `static/src/scss/theme.scss` | Component rules targeting Odoo's structural classes (`.btn`, `.o_input`, `.o_form_sheet`, `.o_kanban_record`, `.o_list_table`, `.o_control_panel`, `.o_home_menu`, `.fc-*`, gantt/grid/cohort…), all scoped under `.o_aic_theme`. Never touches layout or DOM. | the theme's whole stylesheet (this theme + Workspace) measured on Odoo 20: ≈ 225 KB minified / **26 KB gzipped** of the 234 KB gzipped backend CSS; the backlight's per-app selectors are a good part of it |
| `static/src/scss/form_view.scss` | Form-view UX pass (flat notebook tabs, calm x2many edit rows, aligned labels, mobile card rows). | part of the same bundle |
| `static/src/scss/discuss.scss` | Discuss, chat windows and the messaging menu, redesigned rather than re-skinned: depth is semantic (raised = incoming/actionable, seated = yours/selected, flat = the rest), no bubble tints, teal send key. See `docs/neumorphic/discuss_ux.md`. | part of the same bundle |
| `static/src/scss/backlight.scss` | App *backlight*: every app is a keycap — the key (home-menu icon, navbar tile, Apps card) stays clay, the legend (app name) glows in the hue of the app's official Odoo icon, light bleeds evenly round the key and the Apps card takes a very low uniform tint. 64 apps mapped by root-menu xml-id / icon URL (Apps and Settings included); Discuss is deliberately neutral. Intensities are the `--nm-bl-*` tokens. | part of the same bundle |
| `models/ir_http.py` | Adds one boolean (`aic_theme_enabled`) to the webclient bootstrap qcontext. | one `get_param` per page load |
| `views/webclient_templates.xml` | Inherits `web.webclient_bootstrap` to add `o_aic_theme` to `<body>` when enabled. | none |
| `models/res_config_settings.py` + view | The Settings toggle. | none at runtime |

No JS, no OWL patches, no template overrides of components, no extra HTTP requests, no `!important` wars
(the few `!important` used override Odoo's own `!important` utilities). Only `transform`, `box-shadow`,
`opacity`, `background-color`, `color` are transitioned; `prefers-reduced-motion` disables all motion;
`@media print` removes shadows.

## v2 (2026-09-27): depth budget, one accent, one typeface
Decided after the review in `docs/review_2026-09-26/` (screens, measurements, previews).
* **Elevation budget** — three levels, written at the end of `tokens.scss`: *ground* (navbar, control panel, status
  bar, search panel, kanban columns: flat, hairlines or seated wells), *content* (sheet, list slab, cards, dashboard
  tiles, the primary action, the row / card chatter key: `--nm-raised`), *overlay* (dropdowns, dialogs, sheets).
  The navbar casts nothing; section entries are text with a seated pill when open; the control panel is flat with
  ghost buttons; the form's status bar is the sheet's header band (one document, ≈ 40 px higher).
* **Palette** — clay `#E4E8EE` (room for the highlight side of a key), inks `#1F2937 / #4B5563 / #5C6670` (11.9 /
  6.2 / ≈ 4.7 : 1), ONE accent: indigo `#3F54AD` (`--nm-action` is the same colour, kept as a token name). Links are
  ink, underlined on hover; app names are ink (`--nm-bl-legend: 0%`), the hue stays on the key ring. Dark mode keeps
  its lifted values. The relief arcs are off.
* **Typography** — `typography.scss`: Inter (variable, shipped in `static/src/fonts/`, OFL), seven sizes
  (11 · 12 · 13 · 14 · 16 · 20 · 28), three weights (400 · 500 · 600), sentence-case micro labels except list column
  headers, 15 px body and 16 px inputs on phones.
* **Phones** — a record form shows no *New*; its status bar is a bottom action bar pinned above the tab bar (or the
  screen edge without Workspace); kanban cards are 10 / 12 px padded.

## v3 (2026-09-27): mono app icons, hover-only scrollbars, systray pills

* **App icons are one ink.** The theme expects the `identity` module's *symbol* set. Wherever
  identity renders an app icon as a `.o_identity_icon` element (home menu and navbar through
  `identity_enterprise`, the workspace pane on its own), the theme draws option E from tokens: a
  surface-high tile at 78 % of the box with a 26 % radius and a hairline, and the glyph file painted
  through `mask-image` in the muted ink. Hover / active change colours only (tile → active tint with
  an accent hairline, glyph → accent), so the transitions are plain colour fades. Where an icon is
  still an `<img>` (Apps kanban, Settings rail, an app without a glyph file) the file itself is the
  light look and `--nm-icon-rest` handles dark mode; a hover filter is never used because a filter
  transition passes through other hues. A key's fill and shadows never sit on a filtered element.
* **The per-app hue is retired.** `--nm-bl-key`, `--nm-bl-ring` and `--nm-bl-card` are 0 %; the
  `$aic-apps` map still sets `--nm-app` for anything that wants it, but nothing is painted with it.
  The dark legend now honours `--nm-bl-legend` like the light one (ink).
* **Scrollbars.** One rule for every scroll area: thin, no track, thumb transparent until the pointer
  is inside that area (`--nm-scroll-thumb`). Standard properties first, WebKit pseudo-elements as the
  Safari fallback.
* **Systray toggles are pills**, not 50 %: a square toggle is still a circle, the company switcher is
  a stadium with 14 px side padding and an ellipsis (50 % drew an ellipse that clipped the first and
  last letters of a long company name).

## v3.1 (2026-09-27): avatar tags are pills

* Odoo 20's `AvatarTag` carries `.o_avatar` on the whole tag `<span>`, not only on the photo. The
  v3 "round avatar" rule therefore drew every assignee / attendee tag (and every row of the
  avatar autocomplete) as a 50 % ellipse whose shadow tapered away under the first and last
  letters. The rule is now scoped to `<img>`; a tag with a name is a raised stadium with the photo
  seated at its left edge, and Odoo's hover backdrop becomes a tint inside that pill.

## v3.2 / v3.3 (2026-09-27 / 28): kanban stage headers, current stage on the status bar

* **3.2** — Enterprise `kanban_header.scss` inherits the column's box-shadow onto the stage title, so a
  clay column drew a second box around its header. The header is now transparent at rest and clay only
  while sticky.
* **3.3** — Odoo 20 wraps each stage of the form status bar in `div.o_arrow_button_wrap`; the theme's
  direct-child selector missed them, so the stages kept Odoo's chevron clip-path and the current stage was
  not highlighted. The pill segments apply to the wrapped buttons too, and the current stage is the one
  raised key on the track: accent ink, semibold, on the accent tint; its time-in-stage badge takes the same ink.

## v3.4 (2026-09-28): save / discard are keys

The control-panel save (cloud) and discard (X) buttons were a white glyph on nothing and a muted X: an
older "flat until hover" rule in `theme.scss` outranked the A11 rule in `form_view.scss`. That rule is gone;
save is now the filled action key with the accent shadow, discard a raised clay key that turns red on hover.

## Design reference
The design system (tokens, elevation vocabulary, per-component treatment, light/dark values) is documented in
`docs/neumorphic/neumorphic_style_guide.md` of the design repository, with a visual review page
(`odoo_clay_design.html`).

## Customising
Accents live in `tokens.scss` (`$nm-brand` indigo `#4A5FB5`, `$nm-action` teal `#0E8C8C`, both lifted in dark mode).
Override tokens in your own module, after this one, e.g.

```scss
// my_module/static/src/scss/nm_overrides.scss  (bundle: web.assets_backend)
.o_aic_theme {
    --nm-radius: 8px;            // tighter corners
    --nm-d: 4px; --nm-blur: 8px; // flatter shadows
    --nm-bl-legend: 60%;         // calmer backlit app names (0% = plain text)
}
```

To give a custom app a backlight, set its hue on the same hooks `backlight.scss` uses:

```scss
.o_aic_theme .o_home_menu .o_app[data-menu-xmlid="my_module.menu_root"],
.o_aic_theme .o_main_navbar:has(.o_menu_sections [data-menu-xmlid^="my_module."]),
.o_aic_theme .o_modules_kanban .o_kanban_record:has(img[src*="/my_module/static/description/icon"]) { --nm-app: #1DBFA8; }
```

## Odoo 20 notes
* **Icons** — Odoo 20 dropped FontAwesome for Material Symbols (`<i class="oi" data-icon="…"/>`); the few
  glyphs the theme draws itself (a tick, a caret, a plus) use the `aic-glyph()` mixin of `tokens.scss`.
* **Shadow ink** — Odoo 20 moved Enterprise to Bootstrap's light grey scale (the one Community already had), which
  flattened every shadow; `tokens.scss` now mixes the ink from gray-500/600, so both editions share the depth the
  theme was drawn with.
* **Phone forms** — Odoo 20 draws each field of a phone form as an outlined box with a floating label; `mobile.scss`
  turns the box into the clay well (read-only values stay figures on a hairline).
* **Discuss** — the sidebar is now Odoo's messaging menu (tab rail · search · filter pills · rows); `discuss.scss`
  styles it in the Discuss app and in the systray dropdown alike.
* **Enterprise extras** — button gradients are switched off, the segmented `.o_switcher` (view switcher, graph
  toolbars) becomes a clay key row with a seated sliding highlight, coloured tags lose their 1px ring.
* **Settings** — `aic_theme.enabled` is a real boolean in Odoo 20 (`get_bool`): unticking the setting now
  switches the theme off (Odoo 19 deleted the parameter, which read back as "on").
* **Community dark** — the dark variables also go into `web.assets_backend_lazy_dark` (graph, pivot…), which Odoo
  compiles on its own.
* **Readability** — Enterprise now uses Community's light grey scale, where `$o-gray-500` is 1.75:1 on the clay.
  The faint ink (`--nm-text-faint`) takes the value of the Community contrast audit, `#6F7889` (3.7:1), in both
  editions, and the audit's small helper texts (calendar day names, search panel headers, the Discuss tab rail…)
  use the muted ink in both editions.

## Compatibility
Odoo 20.0 Community & Enterprise. Depends on `web`, `base_setup`. Tested on every menu entry of an Enterprise
database with 61 apps (phone and desktop), and on Community with `crm`, `sale_management`, `project`, `calendar`,
`contacts`, `mail`.

## License
OPL-1 (Odoo Proprietary License v1.0). See https://www.odoo.com/documentation/20.0/legal/licenses.html
