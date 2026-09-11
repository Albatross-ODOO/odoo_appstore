/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onWillUnmount, onMounted, onPatched, useExternalListener } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { user } from "@web/core/user";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";

/**
 * Steps of the "Log Client Visit" form. Fields are revealed one at a time:
 * completed steps collapse into compact rows, the active step is expanded
 * and later steps stay hidden until the current one is done.
 */
const VISIT_STEPS = [
    { key: "client",  label: "Client",         required: true,  question: "Who are you visiting?",             hint: "Search an existing contact or type a new company / contact name." },
    { key: "contact", label: "Contact person", required: false, question: "Who did you meet?",                 hint: "The person you spoke with at the client." },
    { key: "phone",   label: "Phone",          required: true,  question: "Their phone number?",               hint: "Used to find or create the contact and avoid duplicates." },
    { key: "email",   label: "Email",          required: false, question: "An email address?",                 hint: "Optional, but helps de-duplicate contacts." },
    { key: "records", label: "Odoo records",   required: false, question: "What should Odoo create?",          hint: "Records are tagged with you as the salesperson." },
    { key: "notes",   label: "Visit notes",    required: false, question: "How did the visit go?",             hint: "Requirements, objections, next steps." },
    { key: "photo",   label: "Visit photo",    required: true,  question: "Take a photo at the client site",   hint: "Verifies your presence at the location." },
    { key: "review",  label: "Review",         required: true,  question: "Everything look right?",            hint: "Tap any step above to edit it before checking out." },
];

const PHOTO_MAX_SIDE = 1280;
const PHOTO_JPEG_QUALITY = 0.82;

/**
 * Downscale an image source (video frame, bitmap or <img>) onto a canvas and
 * return JPEG base64 (without the data: prefix). Keeps uploads small on 4G.
 */
function drawToJpegBase64(canvas, source, width, height) {
    let w = width, h = height;
    if (Math.max(w, h) > PHOTO_MAX_SIDE) {
        const ratio = PHOTO_MAX_SIDE / Math.max(w, h);
        w = Math.round(w * ratio);
        h = Math.round(h * ratio);
    }
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d").drawImage(source, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", PHOTO_JPEG_QUALITY).split(",")[1];
}

/**
 * Read a File picked from the device camera / gallery into JPEG base64.
 * createImageBitmap honours EXIF orientation so phone photos are not rotated.
 */
async function fileToJpegBase64(file) {
    const canvas = document.createElement("canvas");
    if (window.createImageBitmap) {
        const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
        try {
            return drawToJpegBase64(canvas, bitmap, bitmap.width, bitmap.height);
        } finally {
            bitmap.close();
        }
    }
    const url = URL.createObjectURL(file);
    try {
        const img = await new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error("Unsupported image file."));
            image.src = url;
        });
        return drawToJpegBase64(canvas, img, img.naturalWidth, img.naturalHeight);
    } finally {
        URL.revokeObjectURL(url);
    }
}

export class FieldSalesKiosk extends Component {
    static template = "field_sales.FieldSalesKiosk";
    static props = { ...standardActionServiceProps };

    get visitSteps() {
        return VISIT_STEPS;
    }

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
        this.dialog = useService("dialog");
        this.pingInterval = null;

        this.state = useState({
            loading: true,
            session: null,
            activeVisit: null,
            partnerMatches: [],
            partnerSearching: false,
            selectedPartnerId: false,
            selectedPartnerDisplayName: "",
            showPartnerDropdown: false,
            // Full-screen camera viewfinder (check-in / check-out selfie, visit photo)
            showCamera: false,
            cameraMode: "",          // "check_in" | "check_out" | "visit"
            cameraFacing: "user",    // "user" | "environment"
            cameraStarting: false,
            errorMsg: "",
            keyboardOpen: false,
            showVisitModal: false,
            // Geolocation cache for check-in
            latitude: null,
            longitude: null,
            // Visit form state
            companyName: "",
            contactName: "",
            phone: "",
            email: "",
            notes: "",
            createContactBool: false,
            createLeadBool: false,
            visitPhoto: null,
            visitCameraError: "",
            submitting: false,
            // Progressive step form
            visitStep: 0,
            visitMaxStep: 0,
        });

        this.rootRef = useRef("root");
        this.camVideoRef = useRef("camVideo");
        this.camCanvasRef = useRef("camCanvas");
        this.stream = null;
        this._focusedStep = null;
        this._draftVisitId = null;
        this._partnerSearchSeq = 0;
        this._searchPartnersDebounced = debounce((q) => this._searchPartners(q), 250);

        onPatched(() => this._focusActiveStep());
        useExternalListener(window, "keydown", (ev) => this._onWindowKeydown(ev));
        // On phones the on-screen keyboard shrinks the *visual* viewport but not the layout
        // viewport; size the modal from the visual viewport so the footer stays reachable.
        if (window.visualViewport) {
            useExternalListener(window.visualViewport, "resize", () => this._syncViewportHeight());
            useExternalListener(window.visualViewport, "scroll", () => this._syncViewportHeight());
            onMounted(() => this._syncViewportHeight());
        }

        onWillStart(async () => {
            await this.checkActiveSession();
            this.startBackgroundTracking();
        });

        onWillUnmount(() => {
            this.stopBackgroundTracking();
        });
    }

    // ------------------------------------------------------------------
    // Progressive step form helpers
    // ------------------------------------------------------------------
    get visibleSteps() {
        return VISIT_STEPS.slice(0, this.state.visitMaxStep + 1);
    }

    get activeStep() {
        return VISIT_STEPS[this.state.visitStep];
    }

    get progressPercent() {
        return Math.round(((this.state.visitStep + 1) / VISIT_STEPS.length) * 100);
    }

    stepValue(step) {
        const s = this.state;
        switch (step.key) {
            case "client":  return (s.companyName || "").trim();
            case "contact": return (s.contactName || "").trim();
            case "phone":   return (s.phone || "").trim();
            case "email":   return (s.email || "").trim();
            case "records": return s.selectedPartnerId || s.createContactBool || s.createLeadBool ? "x" : "";
            case "notes":   return (s.notes || "").trim();
            case "photo":   return s.visitPhoto || "";
            default:        return "x";
        }
    }

    stepHasValue(step) {
        return !!this.stepValue(step);
    }

    stepSummary(step) {
        const s = this.state;
        switch (step.key) {
            case "client":
                return s.selectedPartnerId ? `${s.companyName} (linked)` : s.companyName || "";
            case "records":
                return this.recordsSummary;
            case "photo":
                return s.visitPhoto ? "Photo captured" : "No photo";
            case "notes":
                return s.notes ? s.notes : "No notes";
            default: {
                const v = this.stepValue(step);
                return v || "Skipped";
            }
        }
    }

    get recordsSummary() {
        const s = this.state;
        const parts = [];
        if (s.selectedPartnerId) {
            parts.push("Linked contact");
        } else if (s.createContactBool) {
            parts.push("New contact");
        }
        if (s.createLeadBool) {
            parts.push("CRM lead");
        }
        return parts.length ? parts.join(" + ") : "Visit log only";
    }

    get canProceed() {
        const step = this.activeStep;
        if (!step) return false;
        if (step.key === "email") {
            const v = (this.state.email || "").trim();
            return !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
        }
        return step.required ? this.stepHasValue(step) : true;
    }

    get nextLabel() {
        const step = this.activeStep;
        if (!step) return "Next";
        if (!step.required && !this.stepHasValue(step)) {
            return step.key === "records" ? "Continue" : "Skip";
        }
        return "Next";
    }

    nextStep() {
        if (!this.canProceed) return;
        if (this.state.visitStep >= VISIT_STEPS.length - 1) return;
        this.state.showPartnerDropdown = false;
        this.state.visitStep += 1;
        this.state.visitMaxStep = Math.max(this.state.visitMaxStep, this.state.visitStep);
    }

    prevStep() {
        if (this.state.visitStep > 0) {
            this.state.showPartnerDropdown = false;
            this.state.visitStep -= 1;
        }
    }

    goToStep(index) {
        if (index >= 0 && index <= this.state.visitMaxStep) {
            this.state.showPartnerDropdown = false;
            this.state.visitStep = index;
        }
    }

    onStepKeydown(ev) {
        if (ev.key === "Enter" && this.activeStep && this.activeStep.key !== "review") {
            ev.preventDefault();
            this.nextStep();
        }
    }

    _focusActiveStep() {
        if (!this.state.showVisitModal) {
            this._focusedStep = null;
            return;
        }
        if (this._focusedStep === this.state.visitStep) return;
        const root = this.rootRef.el;
        const panel = root && root.querySelector(".nm-step-active");
        if (!panel) return;
        this._focusedStep = this.state.visitStep;
        const el = panel.querySelector("[data-autofocus]");
        if (el) {
            el.focus({ preventScroll: true });
        }
        panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }

    _syncViewportHeight() {
        const root = this.rootRef.el;
        const vv = window.visualViewport;
        if (!root || !vv) return;
        root.style.setProperty("--kiosk-vh", `${Math.round(vv.height)}px`);
        root.style.setProperty("--kiosk-vt", `${Math.round(vv.offsetTop)}px`);
        // iOS keeps the layout viewport as-is while the keyboard is up: detect it from the gap
        const keyboardOpen = window.innerHeight - vv.height > 140;
        if (keyboardOpen !== this.state.keyboardOpen) {
            this.state.keyboardOpen = keyboardOpen;
        }
    }

    // ------------------------------------------------------------------
    // Camera viewfinder (shared by selfie verification and visit photo)
    // ------------------------------------------------------------------
    get cameraTitle() {
        switch (this.state.cameraMode) {
            case "check_in":  return _t("Check-in selfie");
            case "check_out": return _t("Check-out selfie");
            default:          return _t("Visit photo");
        }
    }

    get cameraHint() {
        switch (this.state.cameraMode) {
            case "check_in":  return _t("Take a selfie to start your workday.");
            case "check_out": return _t("Take a selfie to end your workday.");
            default:          return _t("Photograph the client site to verify your visit.");
        }
    }

    async openCamera(mode) {
        this.closeCameraStream();
        this.state.cameraMode = mode;
        this.state.cameraFacing = mode === "visit" ? "environment" : "user";
        this.state.errorMsg = "";
        this.state.showCamera = true;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.state.errorMsg = _t("The in-page camera is not available here (it needs HTTPS). Use your phone camera instead.");
            return;
        }
        await new Promise((r) => setTimeout(r, 150)); // let the <video> render
        await this._startCameraStream();
    }

    async _startCameraStream() {
        this.closeCameraStream();
        this.state.cameraStarting = true;
        const facing = this.state.cameraFacing;
        const attempts = [
            { video: { facingMode: { exact: facing }, width: { ideal: 1280 }, height: { ideal: 960 } } },
            { video: { facingMode: facing } },
            { video: true },
        ];
        let stream = null;
        let lastError = null;
        for (const constraints of attempts) {
            try {
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                break;
            } catch (err) {
                lastError = err;
            }
        }
        this.state.cameraStarting = false;
        if (!this.state.showCamera) {
            // closed while waiting for permission
            if (stream) stream.getTracks().forEach((t) => t.stop());
            return;
        }
        if (!stream) {
            this.state.errorMsg = _t("Could not access the camera: ") + (lastError ? lastError.message : "");
            return;
        }
        this.stream = stream;
        const video = this.camVideoRef.el;
        if (video) {
            video.srcObject = stream;
            try {
                await video.play();
            } catch (err) {
                // some mobile browsers refuse autoplay; the frame still renders on user gesture
            }
        }
    }

    flipCamera() {
        this.state.cameraFacing = this.state.cameraFacing === "user" ? "environment" : "user";
        this.state.errorMsg = "";
        this._startCameraStream();
    }

    async captureFromCamera() {
        const video = this.camVideoRef.el;
        if (!this.stream || !video || !this.camCanvasRef.el) {
            return;
        }
        let base64Data;
        try {
            base64Data = drawToJpegBase64(this.camCanvasRef.el, video, video.videoWidth || 640, video.videoHeight || 480);
        } catch (err) {
            this.notification.add(_t("Failed to capture photo: ") + err.message, { type: "danger" });
            return;
        }
        await this._usePhoto(base64Data);
    }

    /** Fallback inside the viewfinder: native camera app / gallery. */
    async onCameraFile(ev) {
        const file = ev.target.files && ev.target.files[0];
        ev.target.value = "";
        if (!file) return;
        try {
            await this._usePhoto(await fileToJpegBase64(file));
        } catch (err) {
            this.notification.add(_t("Could not read the photo: ") + err.message, { type: "danger" });
        }
    }

    async _usePhoto(base64Data) {
        const mode = this.state.cameraMode;
        this.closeCameraStream();
        this.state.showCamera = false;
        this.state.cameraMode = "";
        if (mode === "visit") {
            this.state.visitPhoto = base64Data;
            this.state.visitCameraError = "";
            return;
        }
        await this._submitSelfie(mode, base64Data);
    }

    closeCamera() {
        const mode = this.state.cameraMode;
        this.closeCameraStream();
        this.state.showCamera = false;
        this.state.cameraMode = "";
        this.state.errorMsg = "";
        if (mode !== "visit") {
            this.state.submitting = false; // selfie cancelled: release the check-in/out button
        }
    }

    _onWindowKeydown(ev) {
        if (ev.key !== "Escape") return;
        if (this.state.showCamera) {
            this.closeCamera();
        } else if (this.state.showVisitModal) {
            this.closeVisitModal();
        }
    }

    partnerInitials(p) {
        const name = (p.name || p.display_name || "").trim();
        return name.split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase() || "?";
    }

    get filteredPartners() {
        return this.state.partnerMatches;
    }

    async _searchPartners(query) {
        const q = (query || "").trim();
        const seq = ++this._partnerSearchSeq;
        if (q.length < 2) {
            this.state.partnerMatches = [];
            this.state.partnerSearching = false;
            return;
        }
        this.state.partnerSearching = true;
        try {
            const matches = await this.orm.searchRead(
                "res.partner",
                ["|", "|", ["name", "ilike", q], ["phone", "ilike", q], ["email", "ilike", q]],
                ["id", "display_name", "name", "parent_id", "phone", "mobile", "email", "is_company"],
                { limit: 8, order: "is_company desc, name asc" }
            );
            if (seq === this._partnerSearchSeq) {
                this.state.partnerMatches = matches;
            }
        } catch (err) {
            console.warn("Contact search failed:", err.message);
            if (seq === this._partnerSearchSeq) {
                this.state.partnerMatches = [];
            }
        } finally {
            if (seq === this._partnerSearchSeq) {
                this.state.partnerSearching = false;
            }
        }
    }

    async checkActiveSession() {
        this.state.loading = true;
        try {
            const sessions = await this.orm.searchRead(
                "field.sales.session",
                [["user_id", "=", user.userId], ["state", "=", "checked_in"]],
                ["id", "name", "check_in_time", "total_visits"]
            );
            if (sessions.length > 0) {
                this.state.session = sessions[0];
                const activeVisits = await this.orm.searchRead(
                    "field.sales.visit",
                    [["session_id", "=", sessions[0].id], ["state", "=", "in_progress"]],
                    ["id", "check_in_time", "partner_id", "company_name", "contact_name", "phone", "email"]
                );
                if (activeVisits.length > 0) {
                    this.state.activeVisit = activeVisits[0];
                } else {
                    this.state.activeVisit = null;
                }
            } else {
                this.state.session = null;
                this.state.activeVisit = null;
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
        try {
            const coords = await this.getGPSCoordinates();
            this.state.latitude = coords.latitude;
            this.state.longitude = coords.longitude;
            await this.openCamera("check_in");
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
            this.state.submitting = false;
        }
    }

    async _submitSelfie(mode, base64Data) {
        try {
            if (mode === "check_in") {
                await this.orm.call("field.sales.session", "action_kiosk_check_in", [
                    this.state.latitude,
                    this.state.longitude,
                    base64Data
                ]);
                this.notification.add("Successfully checked in for the day!", { type: "success" });
            } else if (mode === "check_out") {
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
            const actionName = mode === "check_in" ? _t("Check-in") : _t("Check-out");
            this.notification.add(`${actionName} ${_t("failed")}: ` + err.message, { type: "danger" });
        } finally {
            this.state.submitting = false;
        }
    }

    closeCameraStream() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    async onStartClientVisit() {
        if (!this.state.session) return;
        this.state.submitting = true;
        try {
            const coords = await this.getGPSCoordinates();
            const res = await this.orm.call("field.sales.session", "action_kiosk_start_visit", [
                this.state.session.id,
                coords.latitude,
                coords.longitude,
                coords.accuracy,
            ]);
            this.state.activeVisit = {
                id: res.visit_id,
                check_in_time: res.check_in_time,
            };
            this.notification.add("Client visit started! Checked in to client site.", { type: "success" });
            this.openVisitModal();
        } catch (err) {
            this.notification.add("Failed to start client visit: " + err.message, { type: "danger" });
        } finally {
            this.state.submitting = false;
        }
    }

    openVisitModal() {
        const visitId = this.state.activeVisit ? this.state.activeVisit.id : null;
        if (visitId && this._draftVisitId === visitId) {
            // Re-opening the form for the same client visit: keep what was typed
            this._focusedStep = null;
            this.state.showVisitModal = true;
            return;
        }
        this._draftVisitId = visitId;
        this.state.partnerMatches = [];
        this.state.selectedPartnerId = false;
        this.state.selectedPartnerDisplayName = "";
        this.state.showPartnerDropdown = false;
        this.state.companyName = "";
        this.state.contactName = "";
        this.state.phone = "";
        this.state.email = "";
        this.state.notes = "";
        this.state.createContactBool = false;
        this.state.createLeadBool = false;
        this.state.visitPhoto = null;
        this.state.visitCameraError = "";
        this.state.visitCheckInTime = new Date().toISOString();
        this.state.visitStep = 0;
        this.state.visitMaxStep = 0;
        this._focusedStep = null;
        this.state.showVisitModal = true;
    }

    closeVisitModal() {
        this.state.showPartnerDropdown = false;
        this.state.showVisitModal = false;
    }

    selectPartner(partner) {
        this.state.selectedPartnerId = partner.id;
        this.state.selectedPartnerDisplayName = partner.display_name || partner.name;
        if (partner.is_company) {
            this.state.companyName = partner.name || partner.display_name;
            this.state.contactName = "";
        } else if (partner.parent_id) {
            this.state.companyName = partner.parent_id[1];
            this.state.contactName = partner.name;
        } else {
            this.state.companyName = partner.name;
            this.state.contactName = partner.name;
        }
        this.state.phone = partner.phone || partner.mobile || "";
        this.state.email = partner.email || "";
        this.state.showPartnerDropdown = false;
        this.state.createContactBool = false;
    }

    selectCreateNewPartner() {
        this.state.selectedPartnerId = false;
        this.state.selectedPartnerDisplayName = "";
        this.state.showPartnerDropdown = false;
        this.state.createContactBool = true;
    }

    clearSelectedPartner() {
        this.state.selectedPartnerId = false;
        this.state.selectedPartnerDisplayName = "";
        this.state.companyName = "";
        this.state.contactName = "";
        this.state.phone = "";
        this.state.email = "";
        this.state.showPartnerDropdown = false;
    }

    startVisitCamera() {
        this.state.visitCameraError = "";
        return this.openCamera("visit");
    }

    /** "Phone camera" button on the photo step: native camera app / gallery. */
    async onVisitPhotoFile(ev) {
        const file = ev.target.files && ev.target.files[0];
        ev.target.value = "";
        if (!file) return;
        try {
            this.state.visitPhoto = await fileToJpegBase64(file);
            this.state.visitCameraError = "";
        } catch (err) {
            this.notification.add(_t("Could not read the photo: ") + err.message, { type: "danger" });
        }
    }

    // Input handlers
    onCompanyNameInput(ev) {
        this.state.companyName = ev.target.value;
        this.state.showPartnerDropdown = true;
        if (this.state.selectedPartnerId) {
            this.state.selectedPartnerId = false;
            this.state.selectedPartnerDisplayName = "";
        }
        this._searchPartnersDebounced(this.state.companyName);
    }

    onCompanyNameFocus() {
        if (this.state.companyName && this.state.companyName.trim().length > 0) {
            this.state.showPartnerDropdown = true;
        }
    }

    onContactNameInput(ev) {
        this.state.contactName = ev.target.value;
    }

    onPhoneInput(ev) {
        this.state.phone = ev.target.value;
    }

    onEmailInput(ev) {
        this.state.email = ev.target.value;
    }

    onNotesInput(ev) {
        this.state.notes = ev.target.value;
    }

    onCreateContactChange(ev) {
        this.state.createContactBool = ev.target.checked;
    }

    onCreateLeadChange(ev) {
        this.state.createLeadBool = ev.target.checked;
    }

    async submitVisit() {
        if (!this.state.companyName.trim()) {
            this.notification.add("Company or contact name is required.", { type: "warning" });
            this.goToStep(0);
            return;
        }
        if (!this.state.phone.trim()) {
            this.notification.add("Phone number is required.", { type: "warning" });
            this.goToStep(VISIT_STEPS.findIndex((s) => s.key === "phone"));
            return;
        }
        if (!this.state.visitPhoto) {
            this.notification.add("Please capture a photo before completing the client visit.", { type: "warning" });
            this.goToStep(VISIT_STEPS.findIndex((s) => s.key === "photo"));
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
                this.state.visitCheckInTime,
                this.state.email,
                this.state.createContactBool,
                this.state.createLeadBool,
                this.state.selectedPartnerId || false,
                this.state.activeVisit ? this.state.activeVisit.id : false,
            ]);

            this.state.showVisitModal = false;
            this.state.activeVisit = null;
            this._draftVisitId = null;
            await this.checkActiveSession();
            this.notification.add("Client visit completed and checked out successfully!", { type: "success" });
        } catch (err) {
            this.notification.add("Failed to log visit: " + err.message, { type: "danger" });
        } finally {
            this.state.submitting = false;
        }
    }

    onCheckOut() {
        if (!this.state.session || !this.state.session.total_visits || this.state.session.total_visits <= 0) {
            this.notification.add(_t("You must log at least one client visit before checking out."), { type: "warning" });
            return;
        }
        if (this.state.activeVisit) {
            this.notification.add(_t("Please complete your current client visit before checking out."), { type: "warning" });
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("End your workday?"),
            body: _t("You will be asked for a check-out selfie and your GPS position will be recorded."),
            confirmLabel: _t("Check out"),
            cancelLabel: _t("Stay checked in"),
            confirm: () => this._doCheckOut(),
        });
    }

    async _doCheckOut() {
        this.state.submitting = true;
        try {
            const coords = await this.getGPSCoordinates();
            this.state.latitude = coords.latitude;
            this.state.longitude = coords.longitude;
            await this.openCamera("check_out");
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
