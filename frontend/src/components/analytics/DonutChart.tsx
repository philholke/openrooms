"use client";

interface DonutChartProps {
  data: { label: string; value: number; color: string }[];
  size?: number;
}

const DEFAULT_COLORS = [
  "#18181b",
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
];

export default function DonutChart({ data, size = 160 }: DonutChartProps) {
  if (data.length === 0 || data.every((d) => d.value === 0)) {
    return (
      <div
        className="flex items-center justify-center text-zinc-400 text-sm"
        style={{ width: size, height: size }}
      >
        No data
      </div>
    );
  }

  const total = data.reduce((sum, d) => sum + d.value, 0);
  const center = size / 2;
  const radius = size / 2 - 8;
  const innerRadius = radius * 0.6;

  let startAngle = -Math.PI / 2; // Start from top
  const segments = data.map((d, i) => {
    const angle = (d.value / total) * Math.PI * 2;
    const endAngle = startAngle + angle;

    const x1 = center + radius * Math.cos(startAngle);
    const y1 = center + radius * Math.sin(startAngle);
    const x2 = center + radius * Math.cos(endAngle);
    const y2 = center + radius * Math.sin(endAngle);
    const ix1 = center + innerRadius * Math.cos(startAngle);
    const iy1 = center + innerRadius * Math.sin(startAngle);
    const ix2 = center + innerRadius * Math.cos(endAngle);
    const iy2 = center + innerRadius * Math.sin(endAngle);

    const largeArc = angle > Math.PI ? 1 : 0;

    const path = [
      `M ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
      `L ${ix2} ${iy2}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix1} ${iy1}`,
      "Z",
    ].join(" ");

    startAngle = endAngle;

    return {
      path,
      color: d.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length],
      label: d.label,
      value: d.value,
      pct: Math.round((d.value / total) * 100),
    };
  });

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size}>
        {segments.map((s, i) => (
          <path key={i} d={s.path} fill={s.color} opacity={0.85}>
            <title>
              {s.label}: {s.value} ({s.pct}%)
            </title>
          </path>
        ))}
        <text
          x={center}
          y={center - 4}
          textAnchor="middle"
          className="fill-zinc-900 font-semibold"
          fontSize={18}
        >
          {total}
        </text>
        <text
          x={center}
          y={center + 12}
          textAnchor="middle"
          className="fill-zinc-400"
          fontSize={10}
        >
          total
        </text>
      </svg>
      <div className="flex flex-col gap-1.5">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-sm inline-block"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-zinc-600">
              {s.label}{" "}
              <span className="text-zinc-400">({s.pct}%)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
