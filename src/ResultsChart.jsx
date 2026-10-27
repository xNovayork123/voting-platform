import React from "react";
import "./ResultsChart.css";

const COLORS = ["#1a56db", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

function polarToCartesian(cx, cy, r, angleDeg) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export default function ResultsChart({ results, total }) {
  const entries = Object.entries(results || {});
  const size = 160;
  const cx = size / 2;
  const cy = size / 2;
  const r = 58;
  const stroke = 22;

  if (!total) {
    return (
      <div className="chart-empty">
        <div className="donut-placeholder" />
        <p>No votes yet</p>
      </div>
    );
  }

  let angle = 0;
  const segments = entries.map(([label, count], i) => {
    const pct = count / total;
    const start = angle;
    const end = angle + pct * 360;
    angle = end;
    return { label, count, pct, start, end, color: COLORS[i % COLORS.length] };
  });

  return (
    <div className="chart-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut" role="img" aria-label="Results chart">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--donut-track, #eef2f7)" strokeWidth={stroke} />
        {segments.map((s, i) =>
          s.count === 0 ? null : s.pct >= 0.999 ? (
            <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={s.color} strokeWidth={stroke} />
          ) : (
            <path
              key={i}
              d={describeArc(cx, cy, r, s.start, s.end)}
              fill="none"
              stroke={s.color}
              strokeWidth={stroke}
            />
          )
        )}
        <text x={cx} y={cy - 2} textAnchor="middle" className="donut-total">{total}</text>
        <text x={cx} y={cy + 15} textAnchor="middle" className="donut-total-label">votes</text>
      </svg>

      <ul className="chart-legend">
        {segments.map((s, i) => (
          <li key={i}>
            <span className="legend-dot" style={{ background: s.color }} />
            <span className="legend-label">{s.label}</span>
            <span className="legend-val">{s.count} · {Math.round(s.pct * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
