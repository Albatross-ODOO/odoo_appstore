# Gate Management (Gate Desk)

Visitor, vehicle, material and workforce gate control for Odoo, built for the security guard at the barrier
and the gate manager in the back office. Works on Odoo Community and Enterprise (`base`, `mail`, `web` only).

## Roles
* **Security Guard** — sees only the Gate Desk app: Home, Walk-In Entry, Verify Invitation, Worker Attendance, Schedule Visit.
* **Gate Manager** — everything above plus Operations (entries, inside now, worker attendance), Gate Pages and Workforce (profiles, shift logs, break logs).

## Install
1. Copy `gate_management` into an addons path and restart Odoo.
2. Apps → Update Apps List → install **Gate Management**.
3. Settings → Users: assign *Gate Management / Security Guard* or *Gate Manager*.
4. Serve Odoo over HTTPS so phones and tablets allow camera access. Without a camera (plain HTTP, a PC without
   webcam) the guard uses **Upload photo** to attach a picture instead.

## Several databases on one server
Visitors open the digital pass link (`/gate/invitation/share?...`) without logging in, so Odoo has to know which
database the link belongs to. With a single database this is automatic. On a server that hosts several databases,
set `dbfilter` (for example `dbfilter = ^%d$` with one domain per database) or `db_name` in the Odoo configuration;
otherwise visitors get "404 Not Found" on the link. The `db=` parameter in the link alone is not enough.

## WhatsApp
On Odoo Enterprise with the **WhatsApp** app installed, the WhatsApp buttons appear automatically. The Meta template
*Gate Pass Invitation* is created on first use under WhatsApp → Templates; submit it for approval. Until it is approved the
pass opens in WhatsApp as a pre-filled message. On Community the WhatsApp option is hidden.

## Optional
* `gate_management.sms_gateway` system parameter: name of your SMS gateway (OTP messages are logged in the chatter).
* The cron *Gate Entry: Auto Exit Expired Entries* closes entries whose scheduled end has passed (every 30 minutes).
