"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import SummaryCard from "@/components/analytics/SummaryCard";
import BarChart from "@/components/analytics/BarChart";
import LineChart from "@/components/analytics/LineChart";
import DonutChart from "@/components/analytics/DonutChart";
import DateRangePicker from "@/components/analytics/DateRangePicker";
import type {
  ReservationAnalytics,
  GuestAnalytics,
  OperationsAnalytics,
} from "@/lib/types";

const TABS = ["Reservations", "Guests", "Operations"] as const;
type Tab = (typeof TABS)[number];

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split("T")[0];
}
function todayStr(): string {
  return new Date().toISOString().split("T")[0];
}

const SOURCE_COLORS: Record<string, string> = {
  widget: "#3b82f6",
  manual: "#18181b",
  admin: "#18181b",
  walk_in: "#10b981",
  phone: "#f59e0b",
  unknown: "#a1a1aa",
};

export default function AnalyticsPage() {
  const { current: venue } = useVenue();
  const [tab, setTab] = useState<Tab>("Reservations");
  const [dateFrom, setDateFrom] = useState(daysAgo(30));
  const [dateTo, setDateTo] = useState(todayStr());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resData, setResData] = useState<ReservationAnalytics | null>(null);
  const [guestData, setGuestData] = useState<GuestAnalytics | null>(null);
  const [opsData, setOpsData] = useState<OperationsAnalytics | null>(null);

  const fetchData = async () => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      if (tab === "Reservations") {
        const data = await api.get<ReservationAnalytics>(
          `/venues/${venue.id}/analytics/reservations?date_from=${dateFrom}&date_to=${dateTo}&granularity=day`
        );
        setResData(data);
      } else if (tab === "Guests") {
        const data = await api.get<GuestAnalytics>(
          `/analytics/guests?date_from=${dateFrom}&date_to=${dateTo}&granularity=month`
        );
        setGuestData(data);
      } else {
        const data = await api.get<OperationsAnalytics>(
          `/venues/${venue.id}/analytics/operations?date_from=${dateFrom}&date_to=${dateTo}`
        );
        setOpsData(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [venue, tab, dateFrom, dateTo]);

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
  };

  const handleDownloadCsv = () => {
    if (!venue) return;
    let url: string;
    if (tab === "Reservations") {
      url = `/venues/${venue.id}/analytics/reservations?date_from=${dateFrom}&date_to=${dateTo}&granularity=day&format=csv`;
    } else if (tab === "Guests") {
      url = `/analytics/guests?date_from=${dateFrom}&date_to=${dateTo}&granularity=month&format=csv`;
    } else {
      url = `/venues/${venue.id}/analytics/operations?date_from=${dateFrom}&date_to=${dateTo}&format=csv`;
    }
    // Open CSV download in new tab (auth handled by cookies/headers)
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = localStorage.getItem("access_token");
    fetch(`${base}/api/v1${url}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${tab.toLowerCase()}-${dateFrom}-to-${dateTo}.csv`;
        a.click();
      });
  };

  if (!venue) {
    return <div className="p-6 text-zinc-500">Select a venue to view analytics.</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-zinc-900">Analytics</h1>
        <button
          onClick={handleDownloadCsv}
          className="text-xs bg-white border border-zinc-200 text-zinc-600 px-3 py-1.5 rounded-md hover:border-zinc-300 transition-colors"
        >
          Download CSV
        </button>
      </div>

      {/* Date range */}
      <div className="mb-6">
        <DateRangePicker
          dateFrom={dateFrom}
          dateTo={dateTo}
          onChange={handleDateChange}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-zinc-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-zinc-900 text-zinc-900"
                : "border-transparent text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center text-zinc-400 py-12">Loading analytics...</div>
      )}

      {/* ─── Reservations Tab ─── */}
      {!loading && tab === "Reservations" && resData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <SummaryCard label="Reservations" value={resData.summary.total_reservations} />
            <SummaryCard label="Covers" value={resData.summary.total_covers} />
            <SummaryCard label="Avg Party" value={resData.summary.avg_party_size} />
            <SummaryCard
              label="Completion"
              value={`${(resData.summary.completion_rate * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Cancellation"
              value={`${(resData.summary.cancellation_rate * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="No-show"
              value={`${(resData.summary.no_show_rate * 100).toFixed(0)}%`}
            />
          </div>

          {/* Trend chart */}
          <div className="bg-white rounded-lg border border-zinc-200 p-4">
            <h3 className="text-sm font-medium text-zinc-700 mb-3">
              Reservations Over Time
            </h3>
            <div className="overflow-x-auto">
              <LineChart
                data={resData.by_period.map((p) => ({
                  label: p.period.slice(5), // MM-DD
                  value: p.reservations,
                }))}
                height={200}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Source breakdown */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                Booking Source
              </h3>
              <DonutChart
                data={resData.by_source.map((s) => ({
                  label: s.source,
                  value: s.count,
                  color: SOURCE_COLORS[s.source] || "#a1a1aa",
                }))}
              />
            </div>

            {/* Day of week */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                By Day of Week
              </h3>
              <BarChart
                data={resData.by_day_of_week.map((d) => ({
                  label: d.label.slice(0, 3),
                  value: d.covers,
                }))}
                height={160}
              />
            </div>
          </div>

          {/* Peak hours */}
          <div className="bg-white rounded-lg border border-zinc-200 p-4">
            <h3 className="text-sm font-medium text-zinc-700 mb-3">
              Peak Hours
            </h3>
            <BarChart
              data={resData.peak_hours.map((h) => ({
                label: `${h.hour}:00`,
                value: h.covers,
                color: h.covers > (resData.summary.total_covers / Math.max(resData.peak_hours.length, 1)) * 1.5
                  ? "#ef4444"
                  : "#18181b",
              }))}
              height={160}
            />
          </div>
        </div>
      )}

      {/* ─── Guests Tab ─── */}
      {!loading && tab === "Guests" && guestData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <SummaryCard label="Total Guests" value={guestData.summary.total_guests} />
            <SummaryCard label="New (period)" value={guestData.summary.new_guests_in_period} />
            <SummaryCard label="Returning" value={guestData.summary.returning_guests_in_period} />
            <SummaryCard
              label="Return Rate"
              value={`${(guestData.summary.return_rate * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Avg Visits"
              value={guestData.summary.avg_visits_per_guest}
            />
          </div>

          {/* Growth chart */}
          <div className="bg-white rounded-lg border border-zinc-200 p-4">
            <h3 className="text-sm font-medium text-zinc-700 mb-3">
              Guest Growth
            </h3>
            <div className="overflow-x-auto">
              <LineChart
                data={guestData.growth.map((g) => ({
                  label: g.period.slice(0, 7), // YYYY-MM
                  value: g.cumulative,
                }))}
                height={200}
                color="#3b82f6"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top guests */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                Top Guests
              </h3>
              {guestData.top_guests.length === 0 ? (
                <p className="text-zinc-400 text-sm">No visits in this period</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-zinc-500 text-xs border-b border-zinc-100">
                      <th className="py-1.5">Name</th>
                      <th className="py-1.5 text-right">Visits</th>
                      <th className="py-1.5 text-right">Last Visit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {guestData.top_guests.map((g) => (
                      <tr
                        key={g.id}
                        className="border-b border-zinc-50 cursor-pointer hover:bg-zinc-50"
                        onClick={() => window.location.href = `/dashboard/guests/${g.id}`}
                      >
                        <td className="py-1.5 text-zinc-900">{g.name}</td>
                        <td className="py-1.5 text-right text-zinc-600">{g.visits}</td>
                        <td className="py-1.5 text-right text-zinc-400">{g.last_visit || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Tag distribution */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                Tag Distribution
              </h3>
              {guestData.tag_distribution.length === 0 ? (
                <p className="text-zinc-400 text-sm">No tags assigned</p>
              ) : (
                <BarChart
                  data={guestData.tag_distribution.map((t) => ({
                    label: t.tag_name.length > 8 ? t.tag_name.slice(0, 8) + "..." : t.tag_name,
                    value: t.count,
                    color: t.color || "#18181b",
                  }))}
                  height={160}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Operations Tab ─── */}
      {!loading && tab === "Operations" && opsData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <SummaryCard
              label="Avg Turn Time"
              value={opsData.summary.avg_turn_time_minutes != null
                ? `${opsData.summary.avg_turn_time_minutes} min`
                : "—"}
            />
            <SummaryCard
              label="Walk-in Ratio"
              value={`${(opsData.summary.walk_in_ratio * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Waitlist Conversion"
              value={`${(opsData.summary.waitlist_conversion_rate * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Waitlist Abandon"
              value={`${(opsData.summary.waitlist_abandonment_rate * 100).toFixed(0)}%`}
            />
            <SummaryCard
              label="Avg Wait"
              value={opsData.waitlist_stats.avg_wait_minutes != null
                ? `${opsData.waitlist_stats.avg_wait_minutes} min`
                : "—"}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Section utilization */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                Covers by Section
              </h3>
              <BarChart
                data={opsData.utilization_by_section.map((s) => ({
                  label: s.section.length > 10 ? s.section.slice(0, 10) + "..." : s.section,
                  value: s.covers,
                }))}
                height={160}
              />
            </div>

            {/* Turn time by party size */}
            <div className="bg-white rounded-lg border border-zinc-200 p-4">
              <h3 className="text-sm font-medium text-zinc-700 mb-3">
                Turn Time by Party Size
              </h3>
              <BarChart
                data={opsData.turn_time_by_party_size.map((t) => ({
                  label: `${t.party_size}`,
                  value: t.avg_turn_time_minutes,
                  color: "#3b82f6",
                }))}
                height={160}
              />
            </div>
          </div>

          {/* Waitlist funnel */}
          <div className="bg-white rounded-lg border border-zinc-200 p-4">
            <h3 className="text-sm font-medium text-zinc-700 mb-3">
              Waitlist Outcomes
            </h3>
            <BarChart
              data={[
                { label: "Total", value: opsData.waitlist_stats.total_entries, color: "#18181b" },
                { label: "Seated", value: opsData.waitlist_stats.seated, color: "#10b981" },
                { label: "Cancelled", value: opsData.waitlist_stats.cancelled, color: "#f59e0b" },
                { label: "No-show", value: opsData.waitlist_stats.no_show, color: "#ef4444" },
              ]}
              height={140}
            />
          </div>
        </div>
      )}
    </div>
  );
}
