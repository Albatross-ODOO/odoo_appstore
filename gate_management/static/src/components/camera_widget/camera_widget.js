/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, useRef, onWillDestroy, onMounted, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class GateCamera extends Component {
    static template = "gate_management.GateCamera";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            isCameraOpen: false,
            facingMode: "environment", // Default to rear/back camera
        });

        this.stream = null;

        onWillDestroy(() => {
            this.stopCamera();
        });

        // Auto-open logic when mounted
        onMounted(() => {
            const autoOpenField = this.fieldOptions.auto_open_field;
            if (autoOpenField && this.props.record.data[autoOpenField] && !this.state.isCameraOpen && !this.props.record.data[this.props.name]) {
                this.startCamera();
            }
        });

        // Auto-open logic on props update
        onWillUpdateProps((nextProps) => {
            const options = (nextProps.fieldInfo && nextProps.fieldInfo.options) || nextProps.options || {};
            const autoOpenField = options.auto_open_field;
            if (autoOpenField && nextProps.record.data[autoOpenField] && !this.state.isCameraOpen && !nextProps.record.data[this.props.name]) {
                this.startCamera();
            }
        });
    }

    get fieldOptions() {
        return (this.props.fieldInfo && this.props.fieldInfo.options) || this.props.options || {};
    }

    get imageUrl() {
        const val = this.props.record.data[this.props.name];
        if (!val) return false;

        // If it's a saved record and value is likely a metadata string (short), use URL
        // Base64 images are typically very long.
        if (this.props.record.resId && typeof val === 'string' && val.length < 256) {
            const timestamp = this.props.record.write_date ? new Date(this.props.record.write_date).getTime() : Date.now();
            return `/web/image?model=${this.props.record.resModel}&id=${this.props.record.resId}&field=${this.props.name}&unique=${timestamp}`;
        }

        // Otherwise, assume it is base64 (new capture or unsaved record)
        return `data:image/jpeg;base64,${val}`;
    }

    async startCamera() {
        try {
            this.state.isCameraOpen = true;
            const constraints = {
                video: {
                    facingMode: this.state.facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);

            // Wait for DOM update so videoRef is available
            await new Promise(resolve => requestAnimationFrame(resolve));

            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.play();
            }
        } catch (err) {
            console.error("Camera Error:", err);
            this.state.isCameraOpen = false;
            this.notification.add("Could not access camera. Please ensure permissions are granted and you are using HTTPS.", {
                type: "danger",
            });
        }
    }

    async switchCamera() {
        this.stopCamera();
        this.state.facingMode = this.state.facingMode === "environment" ? "user" : "environment";
        await this.startCamera();
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.state.isCameraOpen = false;
    }

    async capture() {
        if (!this.videoRef.el || !this.canvasRef.el) return;

        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;

        // Set canvas dimensions to match video stream
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to base64 (remove data prefix for Odoo Binary field)
        const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
        const base64Data = dataUrl.split(",")[1];

        // Commit change to record
        await this.props.record.update({ [this.props.name]: base64Data });

        this.stopCamera();

        const autoValidate = Boolean(this.fieldOptions.auto_validate) || this.props.record.resModel === 'gate.verify.otp.wizard';

        if (autoValidate) {
            await this.props.record.save();
            const wizardId = this.props.record.resId;
            if (wizardId) {
                try {
                    const resultAction = await this.orm.call(
                        this.props.record.resModel,
                        "action_confirm_verification",
                        [wizardId]
                    );
                    if (resultAction) {
                        this.actionService.doAction(resultAction);
                    }
                } catch (err) {
                    console.error("Auto confirmation failed:", err);
                    this.notification.add("Could not automatically validate entry: " + (err.message || err.name || err), { type: "danger" });
                }
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
};

registry.category("fields").add("gate_camera", gateCamera);
