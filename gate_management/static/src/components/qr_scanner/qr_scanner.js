/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, useRef, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class GateQrScanner extends Component {
    static template = "gate_management.GateQrScanner";
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
            isScanning: false,
            facingMode: "environment",
        });

        this.stream = null;
        this.scanInterval = null;

        onWillDestroy(() => {
            this.stopScanner();
        });
    }

    async startScanner() {
        try {
            this.state.isScanning = true;
            const constraints = {
                video: {
                    facingMode: this.state.facingMode,
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            await new Promise(resolve => requestAnimationFrame(resolve));

            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.play();
                this.startDecodingLoop();
            }
        } catch (err) {
            console.error("Scanner Error:", err);
            this.state.isScanning = false;
            this.notification.add("Could not access camera. Please ensure permissions are granted and you are using HTTPS.", {
                type: "danger",
            });
        }
    }

    stopScanner() {
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.state.isScanning = false;
    }

    startDecodingLoop() {
        if (!window.jsQR) {
            const script = document.createElement('script');
            script.src = "https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js";
            document.head.appendChild(script);
        }

        this.scanInterval = setInterval(async () => {
            if (!this.videoRef.el || !this.canvasRef.el) return;
            const video = this.videoRef.el;
            const canvas = this.canvasRef.el;
            
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const context = canvas.getContext("2d");
                context.drawImage(video, 0, 0, canvas.width, canvas.height);

                let qrCodeResult = null;

                // Native BarcodeDetector if supported
                if ('BarcodeDetector' in window) {
                    try {
                        const barcodeDetector = new window.BarcodeDetector({ formats: ['qr_code'] });
                        const barcodes = await barcodeDetector.detect(canvas);
                        if (barcodes.length > 0) {
                            qrCodeResult = barcodes[0].rawValue;
                        }
                    } catch (e) {
                        console.warn("Native BarcodeDetector failed, falling back to jsQR:", e);
                    }
                }

                // jsQR fallback
                if (!qrCodeResult && window.jsQR) {
                    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                    const code = window.jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: "dontInvert",
                    });
                    if (code) {
                        qrCodeResult = code.data;
                    }
                }

                if (qrCodeResult) {
                    this.onQrDetected(qrCodeResult);
                }
            }
        }, 300);
    }

    async onQrDetected(codeValue) {
        this.stopScanner();
        this.notification.add(`Scanned QR Code: ${codeValue}`, { type: "success" });

        // Update value of input field
        await this.props.record.update({ [this.props.name]: codeValue });
        
        // Save the wizard record first to guarantee it is saved in DB and has an ID
        await this.props.record.save();

        const wizardId = this.props.record.resId;
        if (wizardId) {
            try {
                const resultAction = await this.orm.call(
                    this.props.record.resModel,
                    "action_verify",
                    [wizardId]
                );
                if (resultAction) {
                    this.actionService.doAction(resultAction);
                }
            } catch (err) {
                console.error("Verification failed:", err);
                this.notification.add("Could not automatically check in. Please verify manually.", { type: "danger" });
            }
        }
    }
}

export const gateQrScanner = {
    component: GateQrScanner,
    supportedTypes: ["char"],
};

registry.category("fields").add("gate_qr_scanner", gateQrScanner);
