"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { formatTime, today, cn } from "@/lib/utils";
import type { Reservation, ReservationStatus } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { ReservationDetail } from "@/components/reservations/ReservationDetail";

const STATUS_TABS: { label: string; filter: string | null }[] = [
  { label: "All", filter: null },
  { label: "Upcoming", filter: "pending,confirmed" },
  { label: "Seated", filter: "arrived,partially_arrived,seated" },
  { label: "Completed", filter: "completed" },
  { label: "Cancelled", filter: "cancelled,no_show" },
];

export default function ReservationsPage() {
  const router = useRouter();
  const { current: venue } = useVenue();
  const [date, setDate] = useState(today());
  const [activeTab, setActiveTab] = useState(0);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Reservation | null>(null);

  const fetchReservations = useCallback(async (signal?: AbortSignal) => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ date, per_page: "50" });
      const statusFilter = STATUS_TABS[activeTab].filter;
      if (statusFilter) params.set("status", statusFilter);

      const res = await api.get<Reservation[]>(
        `/venues/${venue.id}/reservations?${params}`
      );
      if (signal?.aborted) return;
      setReservations(res.data);
      setTotal(res.meta?.total ?? res.data.length);
    } catch (err) {
      if (signal?.aborted) return;
      setError(err instanceof Error ? err.message : "Failed to load reservations");
      setReservations([]);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [venue, date, activeTab]);

  useEffect(() => {
    const controller = new AbortController();
    let delay = 30_000;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        await fetchReservations(controller.signal);
        delay = 30_000; // reset on success
      } catch {
        delay = Math.min(delay * 1.5, 300_000); // backoff, cap 5 min
      }
      if (!controller.signal.aborted) {
        timer = setTimeout(poll, delay);
      }
    };

    fetchReservations(controller.signal);
    timer = setTimeout(poll, delay);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [fetchReservations]);

  if (!venue) {
    return (
      <p className="text-sm text-gray-400">
        No venue selected. Create a venue first.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Reservations</h1>
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchReservations()}
          >
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => router.push("/dashboard/reservations/new")}
          >
            + New Reservation
          </Button>
        </div>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 border-b border-gray-200" role="tablist" aria-label="Reservation status filters">
        {STATUS_TABS.map((tab, i) => (
          <button
            key={tab.label}
            role="tab"
            aria-selected={i === activeTab}
            onClick={() => setActiveTab(i)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              i === activeTab
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">Loading...</p>
      ) : reservations.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          No reservations for this date.
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 font-medium text-gray-500">Time</th>
                <th className="px-4 py-3 font-medium text-gray-500">Guest</th>
                <th className="px-4 py-3 font-medium text-gray-500">Party</th>
                <th className="px-4 py-3 font-medium text-gray-500">Table</th>
                <th className="px-4 py-3 font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 font-medium text-gray-500">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reservations.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelected(r);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Reservation for ${r.guest ? `${r.guest.first_name} ${r.guest.last_name}` : "unknown guest"} at ${r.time}`}
                  className="cursor-pointer hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
                >
                  <td className="px-4 py-3 font-medium">
                    {formatTime(r.time)}
                  </td>
                  <td className="px-4 py-3">
                    {r.guest
                      ? `${r.guest.first_name} ${r.guest.last_name}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">{r.party_size}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {r.table_label || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-3 max-w-48 truncate text-gray-400">
                    {r.special_requests || r.notes || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Count */}
      <p className="text-xs text-gray-400">
        {total} reservation{total !== 1 ? "s" : ""}
      </p>

      {/* Detail modal — sync with latest data from polling */}
      {selected && (
        <ReservationDetail
          reservation={reservations.find((r) => r.id === selected.id) ?? selected}
          open={!!selected}
          onClose={() => setSelected(null)}
          onUpdated={() => fetchReservations()}
        />
      )}
    </div>
  );
}
