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
4. Serve Odoo over HTTPS so phones and tablets allow camera access.

## WhatsApp
On Odoo Enterprise with the **WhatsApp** app installed, the WhatsApp buttons appear automatically. The Meta template
*Gate Pass Invitation* is created on first use under WhatsApp → Templates; submit it for approval. Until it is approved the
pass opens in WhatsApp as a pre-filled message. On Community the WhatsApp option is hidden.

## Optional
* `gate_management.sms_gateway` system parameter: name of your SMS gateway (OTP messages are logged in the chatter).
* The cron *Gate Entry: Auto Exit Expired Entries* closes entries whose scheduled end has passed (every 30 minutes).
