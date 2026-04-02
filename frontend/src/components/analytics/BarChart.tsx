"use client";

interface BarChartProps {
  data: { label: string; value: number; color?: string }[];
  maxValue?: number;
  height?: number;
  showValues?: boolean;
}

export default function BarChart({
  data,
  maxValue,
  height = 200,
  showValues = true,
}: BarChartProps) {
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

  const max = maxValue ?? Math.max(...data.map((d) => d.value), 1);
  const barWidth = Math.max(Math.min(100 / data.length - 2, 40), 8);

  return (
    <svg
      width="100%"
      height={height + 40}
      viewBox={`0 0 ${data.length * (barWidth + 6) + 10} ${height + 40}`}
      className="overflow-visible"
    >
      {data.map((d, i) => {
        const barH = (d.value / max) * height;
        const x = i * (barWidth + 6) + 5;
        const y = height - barH;
        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={barH}
              rx={2}
              fill={d.color || "#18181b"}
              opacity={0.85}
            >
              <title>
                {d.label}: {d.value}
              </title>
            </rect>
            {showValues && d.value > 0 && (
              <text
                x={x + barWidth / 2}
                y={y - 4}
                textAnchor="middle"
                className="fill-zinc-500"
                fontSize={9}
              >
                {d.value}
              </text>
            )}
            <text
              x={x + barWidth / 2}
              y={height + 14}
              textAnchor="middle"
              className="fill-zinc-400"
              fontSize={9}
            >
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
