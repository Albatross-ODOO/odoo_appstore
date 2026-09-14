/** @odoo-module */

import { Component, onMounted, onWillDestroy, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";

/** Remember the guard's last camera choice on this device. */
export function loadFacing(key) {
    try {
        const v = localStorage.getItem(key);
        return v === "user" ? "user" : "environment";
    } catch (e) {
        return "environment";
    }
}
export function saveFacing(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (e) {
        /* private mode: ignore */
    }
}

/** Binary field: capture a photo from the device camera (rear by default, flip to front). */
export class GateCamera extends Component {
    static template = "gate_management.GateCamera";
    static props = {
        ...standardFieldProps,
        autoOpenField: { type: String, optional: true },
        autoValidate: { type: Boolean, optional: true },
        validateMethod: { type: String, optional: true },
    };

    setup() {
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ isCameraOpen: false, facingMode: loadFacing("gd_camera_facing"), busy: false });
        this.stream = null;

        onWillDestroy(() => this.stopCamera());
        onMounted(() => this._maybeAutoOpen(this.props));
        onWillUpdateProps((next) => this._maybeAutoOpen(next));
    }

    _maybeAutoOpen(props) {
        const field = props.autoOpenField;
        if (field && props.record.data[field] && !this.state.isCameraOpen && !props.record.data[props.name] && !props.readonly) {
            this.startCamera();
        }
    }

    get imageUrl() {
        const val = this.props.record.data[this.props.name];
        if (!val) {
            return false;
        }
        // saved records expose binary fields as a size string: fetch through /web/image
        if (this.props.record.resId && typeof val === "string" && val.length < 256) {
            const unique = this.props.record.data.write_date ? new Date(this.props.record.data.write_date).getTime() : Date.now();
            return `/web/image?model=${this.props.record.resModel}&id=${this.props.record.resId}&field=${this.props.name}&unique=${unique}`;
        }
        return `data:image/jpeg;base64,${val}`;
    }

    get otherFacingLabel() {
        return this.state.facingMode === "environment" ? _t("Front") : _t("Back");
    }

    get facingLabel() {
        return this.state.facingMode === "environment" ? _t("Back camera") : _t("Front camera");
    }

    /** Open directly with the chosen camera (idle-state buttons). */
    async openWith(facingMode) {
        this.state.facingMode = facingMode;
        saveFacing("gd_camera_facing", facingMode);
        await this.startCamera();
    }

    async startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.notification.add(_t("This browser cannot access the camera. Use HTTPS and a recent browser."), { type: "danger" });
            return;
        }
        try {
            this.state.isCameraOpen = true;
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: this.state.facingMode }, width: { ideal: 1280 }, height: { ideal: 720 } },
            });
            await new Promise((resolve) => requestAnimationFrame(resolve));
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                await this.videoRef.el.play();
            }
        } catch (err) {
            console.warn("Camera Error:", err);
            this.state.isCameraOpen = false;
            this.notification.add(_t("Could not access the camera. Allow camera permission and use HTTPS."), { type: "danger" });
        }
    }

    async switchCamera() {
        this.stopCamera();
        this.state.facingMode = this.state.facingMode === "environment" ? "user" : "environment";
        saveFacing("gd_camera_facing", this.state.facingMode);
        await this.startCamera();
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        this.state.isCameraOpen = false;
    }

    async capture() {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas || !video.videoWidth) {
            return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Data = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
        await this.props.record.update({ [this.props.name]: base64Data });
        this.stopCamera();

        if (this.props.autoValidate && this.props.record.resId) {
            this.state.busy = true;
            try {
                await this.props.record.save();
                const result = await this.orm.call(
                    this.props.record.resModel,
                    this.props.validateMethod || "action_confirm_verification",
                    [this.props.record.resId]
                );
                if (result) {
                    await this.action.doAction(result);
                }
            } catch (err) {
                console.error("Auto confirmation failed:", err);
                this.notification.add(_t("Could not confirm the entry automatically. Use the Confirm button."), { type: "danger" });
            } finally {
                this.state.busy = false;
            }
        }
    }

    retake() {
        this.props.record.update({ [this.props.name]: false });
        this.startCamera();
    }
}

export const gateCamera = {
    component: GateCamera,
    supportedTypes: ["binary"],
    extractProps: ({ options }) => ({
        autoOpenField: options.auto_open_field,
        autoValidate: Boolean(options.auto_validate),
        validateMethod: options.validate_method,
    }),
};

registry.category("fields").add("gate_camera", gateCamera);
