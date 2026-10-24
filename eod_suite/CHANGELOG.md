# EOD Suite — changelog

Versions are per module: theme `web_theme_eod`, engine `aic_theme`, workspace `aic_workspace`,
Home `aic_home`, WhatsApp `aic_send`, bundle `eod_suite`.

## Glass is now EOD (2026-10-16): web_theme_eod 19.0.3.0.0, eod_suite 19.0.2.0.0
- The look and the suite have a new name: EOD, for End Of Day. Modules `web_theme_glass` -> `web_theme_eod`,
  `glass_suite` -> `eod_suite`; Settings > Backend theme > Look shows "EOD". Nothing changes on screen.
- Upgrading a database that has the Glass modules: update the apps list and install EOD Suite. EOD takes over the
  Glass records in place (palette, colour-field tint, settings) and each company keeps its look; the Glass modules
  are then shown as not installed. Take a backup first.
- Store page: the End Of Day story first, then the features.

## Feedback round (2026-10-15): aic_theme 19.0.1.1.0, aic_home 19.0.1.1.0, web_theme_eod 19.0.2.5.4
- Line app icons: each known app (about 65, Community and Enterprise) gets one line icon in the action colour on
  a light tile, everywhere apps are shown: the app grid, the top bar, Home, the command palette, the left pane.
  Settings > Backend theme > App icons switches back to Odoo's icons; icons chosen in Studio are always kept.
- A Home key at the start of the top bar, on every screen (desktop): one click back to Home.
- Home: the done tick on Missed and Today opens Odoo's Mark Done popover (feedback, Done, Done & Schedule Next).
- Home and Focus scroll to the end of the page.
- Forms: an open autocomplete or dropdown (a task's Assignees) is no longer hidden under the next pane.
- Odoo's purple is gone from the last places it showed: a hovered search filter, tinted status badges
  ("Quotation Sent") and links in buttons now take the theme's colours (Odoo 19 / 20 read Bootstrap's colours
  without the `bs-` prefix).
- Discuss and the chatter: the send key turns the action colour once there is text (Odoo 20's new send key), and
  the composer in Discuss no longer shows your avatar under the "+" key.
- Focus: "Done, follow up" on an activity of a record in another of your companies no longer fails with an
  access error (the queue holds every company's activities; the follow-up is now created in the record's company).

## First release (2026-10-15): web_theme_eod 19.0.2.5.2, eod_suite 19.0.1.0.0
- EOD, a frosted-glass look for the Backend Theme Engine: translucent panes over a soft colour field,
  the Lagoon palette (one calm blue, a pale blue for "you are here"), Geist.
- Forms as a set of panes, list rows and kanban cards as slim panes, segmented notebook tabs, calendar,
  pivot and activity views as panes; dropdowns, dialogs and the command palette as frosted overlays.
- Palettes per company: Lagoon, Graphite & Mint, Iris & Apricot, the company logo's colours, or custom
  colours; the colour field follows the palette, and every role is checked for WCAG AA against the pane.
- Phones: a light glass action dock, a frosted tab bar, glass bottom sheets.
- A Transparency preference (Full / Reduced) per user; the system's "reduce transparency" setting and
  browsers without backdrop-filter get nearly opaque panes.
- Point of Sale and the sign-in pages in EOD, light and dark.
- Shares the whole UX with Slate through the engine: Workspace, Home and Focus, Share on WhatsApp.
