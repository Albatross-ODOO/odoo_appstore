/** @odoo-module **/

import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { escape } from "@web/core/utils/strings";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// Leaflet is only needed by this widget: it is loaded on demand, not shipped in the backend bundle
const LEAFLET_URL = "/field_sales/static/src/libs/leaflet/leaflet";

function loadLeaflet() {
    return Promise.all([loadCSS(`${LEAFLET_URL}.css`), loadJS(`${LEAFLET_URL}.js`)]);
}

/** [lat, lng] or null: an exact 0.0 coordinate means "no GPS fix" */
function latLng(lat, lng) {
    return lat && lng ? [lat, lng] : null;
}

export class RouteMap extends Component {
    static template = "field_sales.SessionRouteMap";
    static props = { ...standardFieldProps };

    setup() {
        this.mapContainerRef = useRef("mapContainer");
        this.resizeObserver = null;
        this.map = null;
        this.sizeInterval = null;
        this.renderedKey = null;

        onWillStart(() => loadLeaflet());
        // Rebuild the map when the form shows another record (pager) or its logs/visits change
        onMounted(() => this.renderMap());
        onPatched(() => this.renderMap());
        onWillUnmount(() => this.destroyMap());
    }

    get gpsData() {
        const record = this.props.record;
        const data = record ? record.data : {};
        return {
            data,
            logs: data.location_log_ids ? data.location_log_ids.records || [] : [],
            visits: data.visit_ids ? data.visit_ids.records || [] : [],
        };
    }

    /** Every coordinate drawn on the map: route logs, check-in / check-out and client visits */
    get gpsPoints() {
        const { data, logs, visits } = this.gpsData;
        return [
            ...logs.map((log) => latLng(log.data.latitude, log.data.longitude)),
            latLng(data.check_in_latitude, data.check_in_longitude),
            latLng(data.check_out_latitude, data.check_out_longitude),
            ...visits.map((visit) => latLng(visit.data.latitude, visit.data.longitude)),
        ].filter(Boolean);
    }

    get hasGpsPoints() {
        return this.gpsPoints.length > 0;
    }

    get mapKey() {
        const record = this.props.record;
        const data = record ? record.data : {};
        const ids = (list) => (list && list.records ? list.records.map((r) => r.resId || r.id) : []);
        return JSON.stringify([record && record.resId, ids(data.location_log_ids), ids(data.visit_ids)]);
    }

    destroyMap() {
        if (this.sizeInterval) {
            clearInterval(this.sizeInterval);
            this.sizeInterval = null;
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }

    renderMap() {
        const key = this.mapKey;
        if (this.map && key === this.renderedKey) {
            return;
        }
        this.destroyMap();
        this.renderedKey = key;
        const mapContainer = this.mapContainerRef.el;
        if (!mapContainer) {
            return;
        }

        // Ensure dimensions
        mapContainer.style.height = "600px";
        mapContainer.style.width = "100%";

        const map = L.map(mapContainer);
        this.map = map;

        // Tile layer (OSM tile usage policy: no subdomains, attribution required)
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        }).addTo(map);

        const { data, logs, visits } = this.gpsData;
        const allPoints = this.gpsPoints;
        // popup texts (kept out of the template literals so the translation export finds them)
        const labels = {
            checkIn: _t("Check-In Location"),
            checkOut: _t("Check-Out Location"),
            ping: _t("Trajectory Ping"),
            visit: _t("Client Visit:"),
        };

        // 1. Route line through the trajectory logs
        const route = logs.map((log) => latLng(log.data.latitude, log.data.longitude)).filter(Boolean);
        if (route.length > 0) {
            L.polyline(route, {
                color: "#4f46e5", // indigo route color
                weight: 5,
                opacity: 0.85,
            }).addTo(map);
        }

        // 2. Check-in marker (green)
        const checkIn = latLng(data.check_in_latitude, data.check_in_longitude);
        if (checkIn) {
            L.circleMarker(checkIn, {
                color: "#059669",
                fillColor: "#10b981",
                fillOpacity: 0.9,
                radius: 9,
                weight: 3,
            }).addTo(map).bindPopup(`<b>${escape(labels.checkIn)}</b>`);
        }

        // 3. Check-out marker (red)
        const checkOut = latLng(data.check_out_latitude, data.check_out_longitude);
        if (checkOut) {
            L.circleMarker(checkOut, {
                color: "#dc2626",
                fillColor: "#ef4444",
                fillOpacity: 0.9,
                radius: 9,
                weight: 3,
            }).addTo(map).bindPopup(`<b>${escape(labels.checkOut)}</b>`);
        }

        // 4. Intermediate trajectory logs (indigo)
        for (const log of logs) {
            const point = latLng(log.data.latitude, log.data.longitude);
            const type = log.data.log_type;
            if (point && type !== "check_in" && type !== "check_out") {
                L.circleMarker(point, {
                    color: "#4f46e5",
                    fillColor: "#6366f1",
                    fillOpacity: 0.7,
                    radius: 5,
                    weight: 2,
                }).addTo(map).bindPopup(`${escape(labels.ping)}`);
            }
        }

        // 5. Client visits (amber)
        for (const visit of visits) {
            const point = latLng(visit.data.latitude, visit.data.longitude);
            const company = visit.data.company_name || _t("Client Visit");
            const notes = visit.data.notes || "";
            if (point) {
                L.circleMarker(point, {
                    color: "#d97706",
                    fillColor: "#f59e0b",
                    fillOpacity: 0.95,
                    radius: 8,
                    weight: 3,
                }).addTo(map).bindPopup(
                    `<b>${escape(labels.visit)}</b> ${escape(company)}<br/><i>${escape(notes)}</i>`
                );
            }
        }

        const fitView = () => {
            if (allPoints.length > 0) {
                map.fitBounds(L.latLngBounds(allPoints), { maxZoom: 16, padding: [24, 24] });
            } else {
                // no GPS point yet: neutral world view, the template shows a hint
                map.setView([20, 0], 2);
            }
        };
        fitView();

        // Invalidate map size when the container becomes visible (e.g. switching tabs)
        this.resizeObserver = new ResizeObserver(() => {
            if (mapContainer.offsetWidth > 0 && mapContainer.offsetHeight > 0) {
                map.invalidateSize();
                fitView();
            }
        });
        this.resizeObserver.observe(mapContainer);

        // Periodic invalidation fallback for the first 5 seconds to handle CSS transition delays
        let count = 0;
        this.sizeInterval = setInterval(() => {
            if (mapContainer.offsetWidth > 0) {
                map.invalidateSize();
            }
            count++;
            if (count >= 10) {
                clearInterval(this.sizeInterval);
                this.sizeInterval = null;
            }
        }, 500);
    }
}

registry.category("fields").add("session_route_map", {
    component: RouteMap,
});
