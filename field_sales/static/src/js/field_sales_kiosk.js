/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { user } from "@web/core/user";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";

export class FieldSalesKiosk extends Component {
    static template = "field_sales.FieldSalesKiosk";
    static props = { ...standardActionServiceProps };

    formatCheckInTime(utcString) {
        if (!utcString) return "";
        try {
            return formatDateTime(deserializeDateTime(utcString));
        } catch (e) {
            return utcString;
        }
    }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.pingInterval = null;

        this.state = useState({
            loading: true,
            session: null,
            showCamera: false,
            showVisitModal: false,
            errorMsg: "",
            cameraMode: "",
            // Geolocation cache for check-in
            latitude: null,
            longitude: null,
            // Visit form state
            companyName: "",
            contactName: "",
            phone: "",
            notes: "",
            visitPhoto: null,
            showVisitCamera: false,
            submitting: false,
        });

        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.visitVideoRef = useRef("visitVideo");
        this.visitCanvasRef = useRef("visitCanvas");
        this.stream = null;

        onWillStart(async () => {
            await this.checkActiveSession();
            this.startBackgroundTracking();
        });

        onWillUnmount(() => {
            this.stopBackgroundTracking();
        });
    }

    async checkActiveSession() {
        this.state.loading = true;
        try {
            const sessions = await this.orm.searchRead(
                "field.sales.session",
                [["user_id", "=", user.userId], ["state", "=", "checked_in"]],
                ["id", "name", "check_in_time", "total_visits", "productive_visits"]
            );
            if (sessions.length > 0) {
                this.state.session = sessions[0];
            } else {
                this.state.session = null;
            }
        } catch (err) {
            this.notification.add("Failed to check active session: " + err.message, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    getGPSCoordinates() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error("GPS/Geolocation is not supported by this browser."));
                return;
            }

            let watchId = null;
            let bestPosition = null;
            
            const timeoutId = setTimeout(() => {
                if (watchId) {
                    navigator.geolocation.clearWatch(watchId);
                }
                if (bestPosition) {
                    resolve({
                        latitude: bestPosition.coords.latitude,
                        longitude: bestPosition.coords.longitude,
                        accuracy: bestPosition.coords.accuracy,
                    });
                } else {
                    reject(new Error("GPS request timed out. Please ensure GPS is enabled and permissions are granted."));
                }
            }, 7000);

            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    // Filter out stale/cached coordinates (older than 10 seconds)
                    const age = Date.now() - position.timestamp;
                    if (age > 10000) {
                        return;
                    }

                    if (!bestPosition || position.coords.accuracy < bestPosition.coords.accuracy) {
                        bestPosition = position;
                    }
                    if (position.coords.accuracy <= 15) {
                        clearTimeout(timeoutId);
                        navigator.geolocation.clearWatch(watchId);
                        resolve({
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy,
                        });
                    }
                },
                (error) => {
                    if (!bestPosition) {
                        clearTimeout(timeoutId);
                        if (watchId) {
                            navigator.geolocation.clearWatch(watchId);
                        }
                        let msg = "Unable to retrieve GPS coordinates.";
                        if (error.code === error.PERMISSION_DENIED) {
                            msg = "GPS access denied. Location permission is required.";
                        } else if (error.code === error.POSITION_UNAVAILABLE) {
                            msg = "GPS location unavailable.";
                        } else if (error.code === error.TIMEOUT) {
                            msg = "GPS request timed out.";
                        }
                        reject(new Error(msg));
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 6000,
                    maximumAge: 0
                }
            );
        });
    }

    async onStartCheckIn() {
        this.state.submitting = true;
        this.state.errorMsg = "";
        try {
            const coords = await this.getGPSCoordinates();
            this.state.latitude = coords.latitude;
            this.state.longitude = coords.longitude;

            this.state.showCamera = true;
            this.state.cameraMode = "check_in";
            setTimeout(async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "user" }
                    });
                    this.stream = stream;
                    if (this.videoRef.el) {
                        this.videoRef.el.srcObject = stream;
                        this.videoRef.el.play();
                    }
                } catch (err) {
                    this.state.errorMsg = "Could not access front camera: " + err.message;
                    this.state.submitting = false;
                }
            }, 150);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
            this.state.submitting = false;
        }
    }

    async capturePhoto() {
        if (!this.stream || !this.videoRef.el || !this.canvasRef.el) {
            return;
        }
        try {
            const video = this.videoRef.el;
            const canvas = this.canvasRef.el;
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const dataUrl = canvas.toDataURL("image/jpeg");
            const base64Data = dataUrl.split(",")[1];

            this.closeCameraStream();
            this.state.showCamera = false;

            if (this.state.cameraMode === "check_in") {
                await this.orm.call("field.sales.session", "action_kiosk_check_in", [
                    this.state.latitude,
                    this.state.longitude,
                    base64Data
                ]);
                this.notification.add("Successfully checked in for the day!", { type: "success" });
            } else if (this.state.cameraMode === "check_out") {
                await this.orm.call("field.sales.session", "action_kiosk_check_out", [
                    this.state.session.id,
                    this.state.latitude,
                    this.state.longitude,
                    base64Data
                ]);
                this.state.session = null;
                this.notification.add("Workday ended. Checked out successfully!", { type: "success" });
            }

            await this.checkActiveSession();
        } catch (err) {
            const actionName = this.state.cameraMode === "check_in" ? "Check-in" : "Check-out";
            this.notification.add(`${actionName} failed: ` + err.message, { type: "danger" });
        } finally {
            this.state.submitting = false;
            this.state.cameraMode = "";
        }
    }

    closeCamera() {
        this.closeCameraStream();
        this.state.showCamera = false;
        this.state.submitting = false;
    }

    closeCameraStream() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    openVisitModal() {
        this.state.companyName = "";
        this.state.contactName = "";
        this.state.phone = "";
        this.state.notes = "";
        this.state.visitPhoto = null;
        this.state.showVisitCamera = false;
        this.state.visitCheckInTime = new Date().toISOString();
        this.state.showVisitModal = true;
    }

    closeVisitModal() {
        this.closeCameraStream();
        this.state.showVisitModal = false;
    }

    async startVisitCamera() {
        this.state.showVisitCamera = true;
        this.state.errorMsg = "";
        setTimeout(async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "user" }
                });
                this.stream = stream;
                if (this.visitVideoRef.el) {
                    this.visitVideoRef.el.srcObject = stream;
                    this.visitVideoRef.el.play();
                }
            } catch (err) {
                this.state.errorMsg = "Could not access camera: " + err.message;
                this.state.showVisitCamera = false;
                this.notification.add(this.state.errorMsg, { type: "danger" });
            }
        }, 150);
    }

    captureVisitPhoto() {
        if (!this.stream || !this.visitVideoRef.el || !this.visitCanvasRef.el) {
            return;
        }
        try {
            const video = this.visitVideoRef.el;
            const canvas = this.visitCanvasRef.el;
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const dataUrl = canvas.toDataURL("image/jpeg");
            this.state.visitPhoto = dataUrl.split(",")[1];

            this.closeCameraStream();
            this.state.showVisitCamera = false;
        } catch (err) {
            this.notification.add("Failed to capture photo: " + err.message, { type: "danger" });
        }
    }

    stopVisitCamera() {
        this.closeCameraStream();
        this.state.showVisitCamera = false;
    }

    // Input handlers
    onCompanyNameInput(ev) {
        this.state.companyName = ev.target.value;
    }

    onContactNameInput(ev) {
        this.state.contactName = ev.target.value;
    }

    onPhoneInput(ev) {
        this.state.phone = ev.target.value;
    }

    onNotesInput(ev) {
        this.state.notes = ev.target.value;
    }

    async submitVisit() {
        if (!this.state.companyName || !this.state.phone) {
            this.notification.add("Company Name and Phone Number are required.", { type: "warning" });
            return;
        }
        if (!this.state.visitPhoto) {
            this.notification.add("Please capture a photo before saving the client visit.", { type: "warning" });
            return;
        }
        this.state.submitting = true;
        try {
            const coords = await this.getGPSCoordinates();
            
            await this.orm.call("field.sales.session", "action_log_visit", [
                this.state.session.id,
                this.state.companyName,
                this.state.contactName,
                this.state.phone,
                this.state.notes,
                coords.latitude,
                coords.longitude,
                coords.accuracy,
                this.state.visitPhoto,
                this.state.visitCheckInTime
            ]);

            this.state.showVisitModal = false;
            await this.checkActiveSession();
            this.notification.add("Client visit logged successfully!", { type: "success" });
        } catch (err) {
            this.notification.add("Failed to log visit: " + err.message, { type: "danger" });
        } finally {
            this.state.submitting = false;
        }
    }

    async onCheckOut() {
        if (!this.state.session || !this.state.session.total_visits || this.state.session.total_visits <= 0) {
            this.notification.add("You must log at least one client visit before checking out.", { type: "warning" });
            return;
        }
        if (!confirm("Are you sure you want to check out and end your workday?")) {
            return;
        }
        this.state.submitting = true;
        this.state.errorMsg = "";
        try {
            const coords = await this.getGPSCoordinates();
            this.state.latitude = coords.latitude;
            this.state.longitude = coords.longitude;

            this.state.showCamera = true;
            this.state.cameraMode = "check_out";
            setTimeout(async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "user" }
                    });
                    this.stream = stream;
                    if (this.videoRef.el) {
                        this.videoRef.el.srcObject = stream;
                        this.videoRef.el.play();
                    }
                } catch (err) {
                    this.state.errorMsg = "Could not access front camera: " + err.message;
                    this.state.submitting = false;
                }
            }, 150);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
            this.state.submitting = false;
        }
    }

    startBackgroundTracking() {
        this.stopBackgroundTracking();
        // Ping every 15 minutes if checked in
        this.pingInterval = setInterval(async () => {
            if (this.state.session && this.state.session.id) {
                try {
                    const coords = await this.getGPSCoordinates();
                    await this.orm.create("field.sales.location.log", [{
                        session_id: this.state.session.id,
                        latitude: coords.latitude,
                        longitude: coords.longitude,
                        log_type: "ping"
                    }]);
                } catch (err) {
                    console.warn("Background ping failed:", err.message);
                }
            }
        }, 15 * 60 * 1000);
    }

    stopBackgroundTracking() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
}

registry.category("actions").add("field_sales_kiosk_action", FieldSalesKiosk);
