"use client";

interface SummaryCardProps {
  label: string;
  value: string | number;
  subtext?: string;
}

export default function SummaryCard({ label, value, subtext }: SummaryCardProps) {
  return (
    <div className="bg-white rounded-lg border border-zinc-200 p-4">
      <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-2xl font-semibold text-zinc-900 mt-1">{value}</p>
      {subtext && (
        <p className="text-xs text-zinc-400 mt-1">{subtext}</p>
      )}
    </div>
  );
}
