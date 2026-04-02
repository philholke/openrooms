"use client";

interface LineChartProps {
  data: { label: string; value: number }[];
  height?: number;
  color?: string;
  showArea?: boolean;
}

export default function LineChart({
  data,
  height = 200,
  color = "#18181b",
  showArea = true,
}: LineChartProps) {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-zinc-400 text-sm"
        style={{ height }}
      >
        No data
      </div>
    );
  }

  const padding = { top: 10, right: 10, bottom: 30, left: 40 };
  const width = Math.max(data.length * 30, 300);
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const max = Math.max(...data.map((d) => d.value), 1);
  const yScale = (v: number) => chartH - (v / max) * chartH + padding.top;
  const xScale = (i: number) =>
    padding.left + (i / Math.max(data.length - 1, 1)) * chartW;

  const points = data.map((d, i) => `${xScale(i)},${yScale(d.value)}`);
  const linePath = `M ${points.join(" L ")}`;
  const areaPath = `${linePath} L ${xScale(data.length - 1)},${yScale(0)} L ${xScale(0)},${yScale(0)} Z`;

  // Y-axis grid lines (4 lines)
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
    y: yScale(frac * max),
    label: Math.round(frac * max).toString(),
  }));

  // X-axis labels — show up to ~8 labels evenly
  const step = Math.max(1, Math.ceil(data.length / 8));

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      className="overflow-visible"
    >
      {/* Grid lines */}
      {gridLines.map((g, i) => (
        <g key={i}>
          <line
            x1={padding.left}
            y1={g.y}
            x2={width - padding.right}
            y2={g.y}
            stroke="#e4e4e7"
            strokeDasharray="3,3"
          />
          <text
            x={padding.left - 6}
            y={g.y + 3}
            textAnchor="end"
            className="fill-zinc-400"
            fontSize={9}
          >
            {g.label}
          </text>
        </g>
      ))}

      {/* Area fill */}
      {showArea && (
        <path d={areaPath} fill={color} opacity={0.08} />
      )}

      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
      />

      {/* Data points */}
      {data.map((d, i) => (
        <circle
          key={i}
          cx={xScale(i)}
          cy={yScale(d.value)}
          r={3}
          fill="white"
          stroke={color}
          strokeWidth={1.5}
        >
          <title>
            {d.label}: {d.value}
          </title>
        </circle>
      ))}

      {/* X-axis labels */}
      {data.map(
        (d, i) =>
          i % step === 0 && (
            <text
              key={i}
              x={xScale(i)}
              y={height - 4}
              textAnchor="middle"
              className="fill-zinc-400"
              fontSize={9}
            >
              {d.label}
            </text>
          )
      )}
    </svg>
  );
}
