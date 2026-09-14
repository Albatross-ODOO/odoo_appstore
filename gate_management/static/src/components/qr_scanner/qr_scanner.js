/** @odoo-module */

import { Component, onWillDestroy, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { loadFacing, saveFacing } from "../camera_widget/camera_widget";

/** Char field for the Verify page: 6-digit keypad, QR camera scan (BarcodeDetector or bundled jsQR),
 *  and a text box for handheld barcode scanners. Verifies automatically. */
export class GateQrScanner extends Component {
    static template = "gate_management.GateQrScanner";
    static props = {
        ...standardFieldProps,
        verifyMethod: { type: String, optional: true },
    };

    setup() {
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.wedgeRef = useRef("wedge");
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ code: "", isScanning: false, busy: false, facingMode: loadFacing("gd_scanner_facing") });
        this.stream = null;
        this.scanInterval = null;
        onWillDestroy(() => this.stopScanner());
    }

    get tiles() {
        return [0, 1, 2, 3, 4, 5].map((i) => ({ i, char: this.state.code[i] || "", cur: i === this.state.code.length }));
    }

    key(k) {
        if (this.state.busy) {
            return;
        }
        if (k === "clr") {
            this.state.code = "";
        } else if (k === "del") {
            this.state.code = this.state.code.slice(0, -1);
        } else if (this.state.code.length < 6) {
            this.state.code += k;
            if (this.state.code.length === 6) {
                setTimeout(() => this.verify(this.state.code), 120);
            }
        }
    }

    onWedgeKey(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.onWedge(ev);
        }
    }

    onWedge(ev) {
        const value = (ev.target.value || "").trim();
        if (value) {
            ev.target.value = "";
            this.verify(value);
        }
    }

    async verify(value) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.props.record.update({ [this.props.name]: value });
            await this.props.record.save();
            const resId = this.props.record.resId;
            if (!resId) {
                return;
            }
            const result = await this.orm.call(this.props.record.resModel, this.props.verifyMethod || "action_verify", [resId]);
            if (result) {
                await this.action.doAction(result);
                if (result.tag === "display_notification") {
                    this.state.code = "";
                }
            }
        } catch (err) {
            console.error("Verification failed:", err);
            this.notification.add(_t("Could not verify the code. Please try again."), { type: "danger" });
            this.state.code = "";
        } finally {
            this.state.busy = false;
        }
    }

    async startScanner() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.notification.add(_t("This browser cannot access the camera. Use HTTPS and a recent browser."), { type: "danger" });
            return;
        }
        try {
            this.state.isScanning = true;
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: this.state.facingMode }, width: { ideal: 640 }, height: { ideal: 480 } },
            });
            await new Promise((resolve) => requestAnimationFrame(resolve));
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                await this.videoRef.el.play();
                this.startDecodingLoop();
            }
        } catch (err) {
            console.warn("Scanner Error:", err);
            this.state.isScanning = false;
            this.notification.add(_t("Could not access the camera. Allow camera permission and use HTTPS."), { type: "danger" });
        }
    }

    get otherFacingLabel() {
        return this.state.facingMode === "environment" ? _t("Front") : _t("Back");
    }

    async switchCamera() {
        this.stopScanner();
        this.state.facingMode = this.state.facingMode === "environment" ? "user" : "environment";
        saveFacing("gd_scanner_facing", this.state.facingMode);
        await this.startScanner();
    }

    stopScanner() {
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        this.state.isScanning = false;
    }

    startDecodingLoop() {
        const detector = "BarcodeDetector" in window ? new window.BarcodeDetector({ formats: ["qr_code"] }) : null;
        this.scanInterval = setInterval(async () => {
            const video = this.videoRef.el;
            const canvas = this.canvasRef.el;
            if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) {
                return;
            }
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const context = canvas.getContext("2d", { willReadFrequently: true });
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            let result = null;
            if (detector) {
                try {
                    const codes = await detector.detect(canvas);
                    if (codes.length) {
                        result = codes[0].rawValue;
                    }
                } catch (e) {
                    /* fall through to jsQR */
                }
            }
            if (!result && window.jsQR) {
                const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                const code = window.jsQR(imageData.data, imageData.width, imageData.height, { inversionAttempts: "dontInvert" });
                if (code) {
                    result = code.data;
                }
            }
            if (result) {
                this.stopScanner();
                this.verify(result);
            }
        }, 300);
    }
}

export const gateQrScanner = {
    component: GateQrScanner,
    supportedTypes: ["char"],
    extractProps: ({ options }) => ({ verifyMethod: options.verify_method }),
};

registry.category("fields").add("gate_qr_scanner", gateQrScanner);
