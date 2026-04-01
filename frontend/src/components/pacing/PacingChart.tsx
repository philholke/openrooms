"use client";

import type { PacingSlot } from "@/lib/types";

interface PacingChartProps {
  slots: PacingSlot[];
  capacity: number;
}

export function PacingChart({ slots, capacity }: PacingChartProps) {
  if (slots.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-gray-400">
        No reservations for this date.
      </p>
    );
  }

  const maxCovers = Math.max(1, capacity, ...slots.map((s) => s.booked_covers));
  const chartHeight = 300;
  const chartWidth = Math.max(600, slots.length * 60);
  const barWidth = 40;
  const gap = 20;
  const paddingLeft = 50;
  const paddingBottom = 40;
  const paddingTop = 20;
  const plotHeight = chartHeight - paddingBottom - paddingTop;

  const scaleY = (value: number) =>
    paddingTop + plotHeight - (value / maxCovers) * plotHeight;

  const capacityY = scaleY(capacity);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white p-4">
      <svg
        width={paddingLeft + slots.length * (barWidth + gap) + gap}
        height={chartHeight}
        className="text-sm"
      >
        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const val = Math.round(maxCovers * frac);
          const y = scaleY(val);
          return (
            <g key={frac}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={paddingLeft + slots.length * (barWidth + gap)}
                y2={y}
                stroke="#f3f4f6"
                strokeWidth={1}
              />
              <text
                x={paddingLeft - 8}
                y={y + 4}
                textAnchor="end"
                className="fill-gray-400"
                style={{ fontSize: 11 }}
              >
                {val}
              </text>
            </g>
          );
        })}

        {/* Capacity threshold line */}
        <line
          x1={paddingLeft}
          y1={capacityY}
          x2={paddingLeft + slots.length * (barWidth + gap)}
          y2={capacityY}
          stroke="#ef4444"
          strokeWidth={1.5}
          strokeDasharray="6 3"
        />
        <text
          x={paddingLeft + slots.length * (barWidth + gap) + 4}
          y={capacityY + 4}
          className="fill-red-500"
          style={{ fontSize: 10 }}
        >
          Cap: {capacity}
        </text>

        {/* Bars */}
        {slots.map((slot, i) => {
          const x = paddingLeft + gap + i * (barWidth + gap);
          const barHeight = (slot.booked_covers / maxCovers) * plotHeight;
          const y = paddingTop + plotHeight - barHeight;
          const overCapacity = slot.booked_covers > capacity;

          return (
            <g key={slot.time}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={3}
                fill={overCapacity ? "#fca5a5" : "#93c5fd"}
                stroke={overCapacity ? "#ef4444" : "#3b82f6"}
                strokeWidth={1}
              />
              {/* Cover count on bar */}
              <text
                x={x + barWidth / 2}
                y={y - 4}
                textAnchor="middle"
                className="fill-gray-700"
                style={{ fontSize: 11, fontWeight: 600 }}
              >
                {slot.booked_covers}
              </text>
              {/* Time label */}
              <text
                x={x + barWidth / 2}
                y={chartHeight - 10}
                textAnchor="middle"
                className="fill-gray-500"
                style={{ fontSize: 10 }}
              >
                {slot.time}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
