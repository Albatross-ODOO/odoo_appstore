/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class RouteMap extends Component {
    static template = "field_sales.SessionRouteMap";
    static props = { ...standardFieldProps };

    setup() {
        this.mapContainerRef = useRef("mapContainer");
        this.resizeObserver = null;

        onMounted(() => {
            const mapContainer = this.mapContainerRef.el;

            if (!mapContainer) {
                console.error("❌ mapContainer not found");
                return;
            }

            // Ensure dimensions
            mapContainer.style.height = "600px";
            mapContainer.style.width = "100%";

            // Create leaflet map instance
            const map = L.map(mapContainer);

            // Add tile layer
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
            }).addTo(map);

            // Extract data from the Odoo Record
            const record = this.props.record;
            const data = record ? record.data : {};

            const points = [];

            // 1. Gather trajectory points from location_log_ids
            const logs = data.location_log_ids ? (data.location_log_ids.records || []) : [];
            for (const log of logs) {
                const lat = log.data.latitude;
                const lng = log.data.longitude;
                if (lat && lng) {
                    points.push([lat, lng]);
                }
            }

            // 2. Fallback center if there are no logs yet (e.g. check-in coords)
            const fallbackLat = data.check_in_latitude || 23.0225;
            const fallbackLng = data.check_in_longitude || 72.5714;

            // 3. Draw route line if trajectory logs exist
            if (points.length > 0) {
                L.polyline(points, {
                    color: '#4f46e5', // indigo route color
                    weight: 5,
                    opacity: 0.85
                }).addTo(map);
                map.fitBounds(points);
            } else {
                map.setView([fallbackLat, fallbackLng], 14);
            }

            // 4. Plot Check-In marker (Green Circle)
            if (data.check_in_latitude && data.check_in_longitude) {
                L.circleMarker([data.check_in_latitude, data.check_in_longitude], {
                    color: '#059669',
                    fillColor: '#10b981',
                    fillOpacity: 0.9,
                    radius: 9,
                    weight: 3
                }).addTo(map).bindPopup("<b>Check-In Location</b>");
            }

            // 5. Plot Check-Out marker (Red Circle)
            if (data.check_out_latitude && data.check_out_longitude) {
                L.circleMarker([data.check_out_latitude, data.check_out_longitude], {
                    color: '#dc2626',
                    fillColor: '#ef4444',
                    fillOpacity: 0.9,
                    radius: 9,
                    weight: 3
                }).addTo(map).bindPopup("<b>Check-Out Location</b>");
            }

            // 6. Plot other intermediate trajectory logs (Indigo Circles)
            for (const log of logs) {
                const lat = log.data.latitude;
                const lng = log.data.longitude;
                const type = log.data.log_type;
                if (lat && lng && type !== 'check_in' && type !== 'check_out') {
                    L.circleMarker([lat, lng], {
                        color: '#4f46e5',
                        fillColor: '#6366f1',
                        fillOpacity: 0.7,
                        radius: 5,
                        weight: 2
                    }).addTo(map).bindPopup("Trajectory Ping");
                }
            }

            // 7. Plot Client Visits (Amber Circles)
            const visits = data.visit_ids ? (data.visit_ids.records || []) : [];
            for (const visit of visits) {
                const vLat = visit.data.latitude;
                const vLng = visit.data.longitude;
                const comp = visit.data.company_name || 'Client Visit';
                const notes = visit.data.notes || '';
                if (vLat && vLng) {
                    L.circleMarker([vLat, vLng], {
                        color: '#d97706',
                        fillColor: '#f59e0b',
                        fillOpacity: 0.95,
                        radius: 8,
                        weight: 3
                    }).addTo(map).bindPopup(`<b>Client Visit:</b> ${comp}<br/><i>${notes}</i>`);
                }
            }

            // Invalidate map size when the container becomes visible (e.g. switching tabs)
            this.resizeObserver = new ResizeObserver(() => {
                if (mapContainer.offsetWidth > 0 && mapContainer.offsetHeight > 0) {
                    map.invalidateSize();
                    if (points.length > 0) {
                        map.fitBounds(points);
                    }
                }
            });
            this.resizeObserver.observe(mapContainer);

            // Periodic invalidation fallback for the first 5 seconds to handle CSS transition delays
            let count = 0;
            const sizeInterval = setInterval(() => {
                if (mapContainer.offsetWidth > 0) {
                    map.invalidateSize();
                }
                count++;
                if (count >= 10) {
                    clearInterval(sizeInterval);
                }
            }, 500);

            console.log("✅ Map loaded successfully with dynamic trajectory points.");
        });

        onWillUnmount(() => {
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }
        });
    }
}

registry.category("fields").add("session_route_map", {
    component: RouteMap,
});