/** @odoo-module */

import { Component, onMounted, onWillDestroy, onWillUpdateProps, proxy, signal, t, useProps } from "@odoo/owl";
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
    // Owl 3: props through useProps, refs as signal.ref() read with this.videoRef(), state as proxy()
    props = useProps({
        ...standardFieldProps,
        autoOpenField: t.string().optional(),
        autoValidate: t.boolean().optional(),
        validateMethod: t.string().optional(),
    });
    videoRef = signal.ref();
    canvasRef = signal.ref();
    fileRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = proxy({ isCameraOpen: false, facingMode: loadFacing("gd_camera_facing"), busy: false });
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
        // Odoo 20: a binary value in record.data is an object {content?, size, filename?, checksum?}
        // (content is the base64 payload, present after a capture; absent on records read from the server).
        const val = this.props.record.data[this.props.name];
        if (!val) {
            return false;
        }
        if (val.content) {
            return `data:image/jpeg;base64,${val.content}`;
        }
        if (this.props.record.resId) {
            const unique = val.checksum || (this.props.record.data.write_date ? new Date(this.props.record.data.write_date).getTime() : Date.now());
            return `/web/image?model=${this.props.record.resModel}&id=${this.props.record.resId}&field=${this.props.name}&unique=${unique}`;
        }
        return false;
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
            this.notification.add(_t("This browser cannot access the camera. Use “Upload photo”, or open Odoo over HTTPS."), { type: "danger" });
            return;
        }
        try {
            this.state.isCameraOpen = true;
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: this.state.facingMode }, width: { ideal: 1280 }, height: { ideal: 720 } },
            });
            await new Promise((resolve) => requestAnimationFrame(resolve));
            const video = this.videoRef();
            if (video) {
                video.srcObject = this.stream;
                await video.play();
            }
        } catch (err) {
            console.warn("Camera Error:", err);
            this.state.isCameraOpen = false;
            this.notification.add(_t("Could not access the camera. Use “Upload photo”, or allow camera permission and use HTTPS."), { type: "danger" });
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
        const video = this.videoRef();
        const canvas = this.canvasRef();
        if (!video || !canvas || !video.videoWidth) {
            return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Data = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
        await this._setPhoto(base64Data);
    }

    /** No camera (HTTP, a PC without webcam): pick a picture file, or take one with the phone's camera app. */
    pickFile() {
        this.fileRef()?.click();
    }

    async onFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        ev.target.value = "";
        if (!file) {
            return;
        }
        if (!(file.type || "").startsWith("image/")) {
            this.notification.add(_t("Choose a picture file."), { type: "warning" });
            return;
        }
        try {
            await this._setPhoto(await this._fileToJpeg(file));
        } catch (err) {
            console.warn("Photo upload:", err);
            this.notification.add(_t("This picture could not be read. Try another one."), { type: "danger" });
        }
    }

    /** Scale the picture down to the camera size (1280 px) and store it as a JPEG like a capture. */
    async _fileToJpeg(file) {
        const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
        let img;
        try {
            img = await new Promise((resolve, reject) => {
                const i = new Image();
                i.onload = () => resolve(i);
                i.onerror = reject;
                i.src = dataUrl;
            });
        } catch (e) {
            // a format the browser cannot draw (e.g. HEIC on a PC): keep the file as it is
            return dataUrl.split(",")[1];
        }
        const scale = Math.min(1, 1280 / Math.max(img.naturalWidth, img.naturalHeight, 1));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
    }

    async _setPhoto(base64Data) {
        // Odoo 20 binary fields are written as {filename, content} (same shape as the core image field)
        await this.props.record.update({ [this.props.name]: { filename: "photo.jpg", content: base64Data } });
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
