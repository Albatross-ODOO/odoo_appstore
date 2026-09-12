# Odoo Gate Management Module

## Overview
A custom Odoo module designed for Warehouse Gate Management. It handles incoming and outgoing flow of vehicles, with support for OTP verification and photo evidence.

## Features
- **Incoming & Outgoing Entries**: Track vehicles entering and leaving.
- **OTP Verification**: Generate and verify OTPs for driver authentication.
- **Photo Upload**: Capture and attach photos of the vehicle/driver.
- **Barcode/QR Scanning**: Scan codes to quick-fill or verify entries.
- **Security Roles**: Dedicated roles for Guards and Managers.

## Installation Guide

### Step 1: Locate your Odoo Addons Directory
Find where your Odoo server looks for custom modules. This is usually defined in your `odoo.conf` file under the `addons_path` parameter.
Common paths:
- `/usr/lib/python3/dist-packages/odoo/addons` (Package install)
- `/opt/odoo/odoo/addons` (Source install)
- Your custom path (e.g., `/home/user/odoo-dev/custom-addons`)

### Step 2: Add the Module
Copy or symlink the `gate_management` folder into your custom addons directory.
**Using CLI:**
```bash
# Example: Copying to custom addons path
cp -r gate_management /path/to/your/custom-addons/
```

### Step 3: Restart Odoo Service
You must restart the Odoo server for it to recognize the new folder.
```bash
# If running as a service
sudo service odoo restart

# If running manually (bin/odoo-bin)
# Stop via Ctrl+C and start again
./odoo-bin -c odoo.conf -u gate_management
```

### Step 4: Update App List
1. Log in to Odoo as Administrator.
2. Activate **Developer Mode**:
   - Go to Settings > Scroll down to "Developer Tools".
   - Click "Activate the developer mode".
3. Go to **Apps**.
4. Click **Update Apps List** in the top menu.
5. Click **Update** in the dialog.

### Step 5: Install the Module
1. In the Apps search bar, remove the "Apps" filter.
2. Search for `Gate Management`.
3. Click **Activate** or **Install**.

## Usage
- **Guards**: Access the "Gate Management" menu to record entries.
- Use "Generate OTP" to create a code.
- Verify the code with the driver.
- Upload photos directly from the mobile interface.
- Mark entry as "Authorized" then "Done".

## Configuration
- **Users**: Assign "Security Guard" or "Gate Manager" roles to users.
- **SMS**: Configure Odoo's SMS gateway to enable actual SMS delivery of OTPs (requires additional configuration).
