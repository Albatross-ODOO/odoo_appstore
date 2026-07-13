# Field Sales Activity & Tracking

## Overview
Field Sales Activity & Tracking is a comprehensive Odoo 18 module designed specifically for field sales representatives and managers. It allows representatives to manage their daily routes by seamlessly checking in and checking out using geolocation and selfies. Managers can easily visualize real-time routes, track durations, and convert activities into direct prospects/leads.

## Key Features
*   **Kiosk Mode:** Mobile-friendly kiosk for sales representatives to start and end their sessions.
*   **Geolocation & Tracking:** Tracks Check-In and Check-Out coordinates with interactive route visualization using Leaflet Maps.
*   **Selfie Verification:** Ensures the physical presence of representatives during check-in and check-out.
*   **Client Visit Logging:** Seamlessly capture company and contact details, and automatically create leads within the Odoo Contacts base.
*   **Automated Lead Generation:** Logs all new prospects under a unique 'Field Lead' category for straightforward filtering and marketing follow-ups.
*   **Performance Metrics & Dashboard:** Track the number of productive visits and durations effortlessly.
*   **End-of-Day PDF Reports:** Automatically generate comprehensive session reports.

## Installation
1. Download the module and add the `field_sales` folder to your Odoo custom addons directory.
2. Update the App List in your Odoo database.
3. Search for "Field Sales Activity & Tracking" and click "Install".

## Configuration
1. Make sure Google Maps or a compatible Maps tool can read standard coordinates if required for external mapping.
2. The module automatically configures two groups: 
   * **Field Sales / User:** Can check-in/out and create client visits.
   * **Field Sales / Administrator:** Can review all users' logs, route maps, and visit history.

## Usage
### For Sales Representatives:
1. Navigate to **Field Sales -> Kiosk Dashboard**.
2. Click **Start Session**, capture a selfie, and allow geolocation access.
3. Use **Log Visit** throughout the day when meeting clients.
4. Click **End Session** when the workday is finished.

### For Managers:
1. Go to **Field Sales -> Activities -> Work Sessions**.
2. Select any session to review check-in/out times, verify location mismatches, and view route maps.
3. Go to **Field Sales -> Prospects** to see automatically generated leads and initiate follow-ups.

## Dependencies
*   `base` (Standard Odoo)
*   `web` (Standard Odoo)

## Support & Feedback
For support, bug reporting, or feature requests, please contact Albatross.

## License
This module is distributed under the **OPL-1 (Odoo Proprietary License v1.0)**.
