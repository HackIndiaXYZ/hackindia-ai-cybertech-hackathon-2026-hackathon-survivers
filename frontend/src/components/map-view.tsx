"use client";

import { MapContainer, TileLayer, CircleMarker, Popup, ZoomControl } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import type { DashboardComplaint } from "@/lib/api";

function markerColor(status: string) {
  if (status === "Resolved") return "#10b981";
  if (status === "In progress") return "#f59e0b";
  if (status === "Rejected") return "#64748b";
  return "#8b5cf6";
}

export default function MapView({ complaints }: { complaints: DashboardComplaint[] }) {
  const valid = complaints.filter(
    (c) => Number.isFinite(c.latitude) && Number.isFinite(c.longitude)
      && c.latitude >= -90 && c.latitude <= 90
      && c.longitude >= -180 && c.longitude <= 180
  );
  const center: LatLngExpression = valid.length
    ? [valid[0].latitude, valid[0].longitude]
    : [22.9734, 78.6569];

  return (
    <div className="relative h-[460px] overflow-hidden rounded-2xl border border-slate-200 shadow-sm">
      <MapContainer
        key={`${center[0]}-${center[1]}-${valid.length}`}
        center={center}
        zoom={valid.length ? 12 : 5}
        scrollWheelZoom
        zoomControl={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ZoomControl position="bottomright" />
        {valid.map((report) => {
          const color = markerColor(report.status);
          const position: LatLngExpression = [report.latitude, report.longitude];
          return (
            <CircleMarker
              key={report.id}
              center={position}
              radius={9}
              pathOptions={{ color: "#ffffff", weight: 3, fillColor: color, fillOpacity: 1 }}
            >
              <Popup>
                <div style={{ minWidth: 170, fontFamily: "Arial, sans-serif" }}>
                  <div style={{ color, fontWeight: 700, fontSize: 11 }}>{report.id} · {report.status}</div>
                  <div style={{ fontWeight: 700, margin: "7px 0" }}>{report.title}</div>
                  <div style={{ color: "#64748b", fontSize: 12 }}>{report.category} · {report.department}</div>
                  <div style={{ color: "#64748b", fontSize: 11, marginTop: 5 }}>{report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}</div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <div className="absolute left-3 top-3 z-[500] rounded-xl border border-white/80 bg-white/95 p-3 shadow-lg backdrop-blur">
        <div className="text-xs font-bold text-slate-800">Backend complaint locations</div>
        <div className="mt-1 text-[10px] text-slate-500">{valid.length} mapped of {complaints.length} loaded reports</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {[
            ["#8b5cf6", "Open"],
            ["#f59e0b", "In progress"],
            ["#10b981", "Resolved"],
          ].map(([color, label]) => (
            <span key={label} className="flex items-center gap-1 text-[10px] text-slate-600">
              <span className="h-2 w-2 rounded-full" style={{ background: color }} />{label}
            </span>
          ))}
        </div>
      </div>
      {valid.length === 0 && (
        <div className="absolute bottom-3 left-3 right-3 z-[500] rounded-xl bg-white/95 p-3 text-xs text-slate-600 shadow">
          No geolocated backend complaints are available yet. Submit a report with coordinates to add a marker.
        </div>
      )}
    </div>
  );
}
