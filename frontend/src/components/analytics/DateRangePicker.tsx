"use client";

interface DateRangePickerProps {
  dateFrom: string;
  dateTo: string;
  onChange: (from: string, to: string) => void;
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split("T")[0];
}

function today(): string {
  return new Date().toISOString().split("T")[0];
}

const PRESETS = [
  { label: "7d", from: () => daysAgo(7), to: today },
  { label: "30d", from: () => daysAgo(30), to: today },
  { label: "90d", from: () => daysAgo(90), to: today },
  {
    label: "YTD",
    from: () => `${new Date().getFullYear()}-01-01`,
    to: today,
  },
];

export default function DateRangePicker({
  dateFrom,
  dateTo,
  onChange,
}: DateRangePickerProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {PRESETS.map((p) => (
        <button
          key={p.label}
          onClick={() => onChange(p.from(), p.to())}
          className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
            dateFrom === p.from() && dateTo === p.to()
              ? "bg-zinc-900 text-white border-zinc-900"
              : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300"
          }`}
        >
          {p.label}
        </button>
      ))}
      <div className="flex items-center gap-1 ml-2">
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => onChange(e.target.value, dateTo)}
          className="text-xs border border-zinc-200 rounded-md px-2 py-1.5"
        />
        <span className="text-zinc-400 text-xs">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => onChange(dateFrom, e.target.value)}
          className="text-xs border border-zinc-200 rounded-md px-2 py-1.5"
        />
      </div>
    </div>
  );
}
