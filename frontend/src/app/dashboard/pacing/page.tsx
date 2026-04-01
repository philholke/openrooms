"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { today } from "@/lib/utils";
import type { PacingSlot } from "@/lib/types";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { PacingChart } from "@/components/pacing/PacingChart";

interface PacingData {
  venue_id: string;
  date: string;
  total_capacity: number;
  slots: PacingSlot[];
}

export default function PacingPage() {
  const { current: venue } = useVenue();
  const [date, setDate] = useState(today());
  const [data, setData] = useState<PacingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPacing = useCallback(async () => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PacingData>(
        `/venues/${venue.id}/pacing?date=${date}`,
      );
      setData(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load pacing data");
    } finally {
      setLoading(false);
    }
  }, [venue, date]);

  useEffect(() => {
    fetchPacing();
  }, [fetchPacing]);

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected</p>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Pacing</h1>
        <div className="flex items-center gap-3">
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40"
          />
          <Button variant="secondary" size="sm" onClick={fetchPacing}>
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : data ? (
        <div>
          <div className="mb-4 flex gap-6 text-sm text-gray-600">
            <p>
              <span className="font-medium text-gray-900">
                {data.slots.reduce((sum, s) => sum + s.booked_covers, 0)}
              </span>{" "}
              booked covers
            </p>
            <p>
              <span className="font-medium text-gray-900">
                {data.total_capacity}
              </span>{" "}
              total capacity
            </p>
            <p>
              <span className="font-medium text-gray-900">
                {data.slots.length}
              </span>{" "}
              time slots
            </p>
          </div>
          <PacingChart slots={data.slots} capacity={data.total_capacity} />

          {/* Legend */}
          <div className="mt-4 flex items-center gap-6 text-xs text-gray-500">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded border border-blue-500 bg-blue-200" />
              <span>Booked covers</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded border border-red-500 bg-red-200" />
              <span>Over capacity</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-0.5 w-6 border-t-2 border-dashed border-red-500" />
              <span>Capacity line</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
