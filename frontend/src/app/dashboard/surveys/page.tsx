"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { cn } from "@/lib/utils";
import type { SurveyStats, Survey } from "@/lib/types";
import { Button } from "@/components/ui/Button";

const DATE_PRESETS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "All time", days: 0 },
];

export default function SurveyDashboardPage() {
  const { current: venue } = useVenue();
  const [stats, setStats] = useState<SurveyStats | null>(null);
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preset, setPreset] = useState(1); // default 30 days

  const fetchData = useCallback(async () => {
    if (!venue) return;
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      const days = DATE_PRESETS[preset].days;
      if (days > 0) {
        const from = new Date();
        from.setDate(from.getDate() - days);
        params.set("date_from", from.toISOString());
      }

      const [statsRes, surveysRes] = await Promise.all([
        api.get<SurveyStats>(`/venues/${venue.id}/surveys/stats?${params}`),
        api.get<Survey[]>(`/venues/${venue.id}/surveys?per_page=10&${params}`),
      ]);

      setStats(statsRes.data);
      setSurveys(surveysRes.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load survey data");
    } finally {
      setLoading(false);
    }
  }, [venue, preset]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected.</p>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Surveys</h1>
        <Button variant="secondary" size="sm" onClick={fetchData}>Refresh</Button>
      </div>

      {/* Date presets */}
      <div className="flex gap-1 border-b border-gray-200" role="tablist">
        {DATE_PRESETS.map((p, i) => (
          <button
            key={p.label}
            role="tab"
            aria-selected={preset === i}
            onClick={() => setPreset(i)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              preset === i
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">Loading...</p>
      ) : stats ? (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-6 gap-3">
            <AvgCard label="Overall" value={stats.avg_overall} />
            <AvgCard label="Food" value={stats.avg_food} />
            <AvgCard label="Service" value={stats.avg_service} />
            <AvgCard label="Ambiance" value={stats.avg_ambiance} />
            <AvgCard label="Drinks" value={stats.avg_drinks} />
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-400">Responses</p>
              <p className="text-lg font-semibold text-gray-900">{stats.total_responses}</p>
            </div>
          </div>

          {/* Rating distribution */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="text-sm font-semibold text-gray-900">Rating Distribution</h2>
            {stats.distribution.map((d) => {
              const pct = stats.total_responses > 0
                ? (d.count / stats.total_responses) * 100
                : 0;
              return (
                <div key={d.rating} className="flex items-center gap-3">
                  <span className="w-12 text-sm text-gray-600">{d.rating} star</span>
                  <div className="flex-1 h-5 rounded bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded bg-yellow-400 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-sm text-gray-500">{d.count}</span>
                </div>
              );
            })}
          </div>

          {/* Recent comments */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="text-sm font-semibold text-gray-900">Recent Responses</h2>
            {surveys.length === 0 ? (
              <p className="text-sm text-gray-400">No survey responses yet.</p>
            ) : (
              <div className="divide-y divide-gray-100">
                {surveys.map((s) => (
                  <div key={s.id} className="py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-yellow-400">
                        {"\u2605".repeat(s.overall_rating)}
                        <span className="text-gray-300">{"\u2605".repeat(5 - s.overall_rating)}</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(s.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {s.comment && (
                      <p className="mt-1 text-sm text-gray-600">{s.comment}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}

function AvgCard({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-lg font-semibold text-gray-900">
        {value != null ? `${value}/5` : "N/A"}
      </p>
    </div>
  );
}
