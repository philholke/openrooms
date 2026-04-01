"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { today } from "@/lib/utils";
import type { FloorPlan, Reservation, TableWithStatus } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { FloorPlanCanvas } from "@/components/floor-plans/FloorPlanCanvas";
import { ServerAssignmentPanel } from "@/components/floor-plans/ServerAssignmentPanel";

const STATUS_COLORS: Record<string, { fill: string; stroke: string }> = {
  available: { fill: "#dcfce7", stroke: "#22c55e" },
  occupied: { fill: "#fee2e2", stroke: "#ef4444" },
  reserved: { fill: "#dbeafe", stroke: "#3b82f6" },
  held: { fill: "#fef3c7", stroke: "#f59e0b" },
};

const LEGEND = [
  { status: "Available", color: "bg-green-100 border-green-500" },
  { status: "Occupied", color: "bg-red-100 border-red-500" },
  { status: "Reserved", color: "bg-blue-100 border-blue-500" },
  { status: "Held", color: "bg-amber-100 border-amber-500" },
];

function AssignTableModal({
  open,
  onClose,
  venueId,
  tableId,
  date,
  onAssigned,
}: {
  open: boolean;
  onClose: () => void;
  venueId: string;
  tableId: string;
  date: string;
  onAssigned: () => void;
}) {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError("");
    api
      .get<Reservation[]>(
        `/venues/${venueId}/reservations?date=${date}&status=pending,confirmed,arrived,partially_arrived&per_page=100`,
      )
      .then((res) => {
        // Filter to unassigned reservations only
        setReservations(res.data.filter((r) => !r.table_id));
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load reservations");
      })
      .finally(() => setLoading(false));
  }, [open, venueId, date]);

  const handleAssign = async (reservationId: string) => {
    try {
      await api.patch(`/reservations/${reservationId}`, { table_id: tableId });
      onAssigned();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign table");
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Assign Reservation to Table">
      {error && (
        <div role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}
      {loading ? (
        <p className="text-sm text-gray-400">Loading reservations...</p>
      ) : reservations.length === 0 ? (
        <p className="text-sm text-gray-400">No unassigned reservations for this date.</p>
      ) : (
        <div className="max-h-80 space-y-2 overflow-y-auto">
          {reservations.map((r) => (
            <button
              key={r.id}
              onClick={() => handleAssign(r.id)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-200 p-3 text-left text-sm hover:bg-gray-50"
            >
              <div>
                <span className="font-medium">
                  {r.guest?.first_name} {r.guest?.last_name}
                </span>
                <span className="ml-2 text-gray-400">
                  {r.time?.slice(0, 5)} &middot; Party of {r.party_size}
                </span>
              </div>
              <span className="text-xs capitalize text-gray-500">{r.status}</span>
            </button>
          ))}
        </div>
      )}
    </Modal>
  );
}

export default function SeatingPage() {
  const { current: venue } = useVenue();
  const [date, setDate] = useState(today());
  const [floorPlans, setFloorPlans] = useState<FloorPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [tables, setTables] = useState<TableWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected table popover
  const [selectedTable, setSelectedTable] = useState<TableWithStatus | null>(null);
  const [showAssign, setShowAssign] = useState(false);
  const [showServers, setShowServers] = useState(false);

  // Load floor plans for venue
  useEffect(() => {
    if (!venue) return;
    api
      .get<FloorPlan[]>(`/venues/${venue.id}/floor-plans`)
      .then((res) => {
        setFloorPlans(res.data);
        if (res.data.length > 0 && !selectedPlanId) {
          setSelectedPlanId(res.data[0].id);
        }
      })
      .catch(() => {});
  }, [venue, selectedPlanId]);

  // Fetch table statuses with polling
  const fetchStatuses = useCallback(
    async (signal?: AbortSignal) => {
      if (!venue) return;
      try {
        const res = await api.get<TableWithStatus[]>(
          `/venues/${venue.id}/table-statuses?date=${date}`,
        );
        if (signal?.aborted) return;
        // Filter to selected floor plan
        const filtered = selectedPlanId
          ? res.data.filter((t) => t.floor_plan_id === selectedPlanId)
          : res.data;
        setTables(filtered);
        setError(null);
      } catch (err) {
        if (signal?.aborted) return;
        setError(err instanceof ApiError ? err.message : "Failed to load table statuses");
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [venue?.id, date, selectedPlanId],
  );

  useEffect(() => {
    if (!venue) return;

    const controller = new AbortController();
    let delay = 15_000;
    let timer: ReturnType<typeof setTimeout>;
    let mounted = true;

    const poll = async () => {
      if (!mounted) return;
      try {
        await fetchStatuses(controller.signal);
        delay = 15_000;
      } catch {
        delay = Math.min(delay * 1.5, 300_000);
      }
      if (mounted && !controller.signal.aborted) {
        timer = setTimeout(poll, delay);
      }
    };

    setLoading(true);
    fetchStatuses(controller.signal).then(() => {
      if (mounted) timer = setTimeout(poll, delay);
    });

    return () => {
      mounted = false;
      controller.abort();
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venue?.id, date, selectedPlanId]);

  // Build status color map
  const statusColorMap: Record<string, { fill: string; stroke: string }> = {};
  for (const t of tables) {
    statusColorMap[t.id] = STATUS_COLORS[t.status] ?? STATUS_COLORS.available;
  }

  // Hold / release table
  const handleHold = async (tableId: string) => {
    const holdUntil = new Date(Date.now() + 60 * 60 * 1000).toISOString(); // 1 hour
    try {
      await api.patch(`/tables/${tableId}/hold`, { held_until: holdUntil });
      fetchStatuses();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to hold table");
    }
  };

  const handleRelease = async (tableId: string) => {
    try {
      await api.patch(`/tables/${tableId}/hold`, { held_until: null });
      fetchStatuses();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to release table");
    }
  };

  // Keep selectedTable in sync
  const currentSelected = selectedTable
    ? tables.find((t) => t.id === selectedTable.id) ?? null
    : null;

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected</p>;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-gray-900">Live Seating</h1>
        <div className="flex items-center gap-3">
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40"
          />
          {floorPlans.length > 1 && (
            <Select
              label=""
              value={selectedPlanId}
              onChange={(e) => setSelectedPlanId(e.target.value)}
              options={floorPlans.map((fp) => ({
                value: fp.id,
                label: fp.name,
              }))}
            />
          )}
          <Button
            variant={showServers ? "primary" : "secondary"}
            size="sm"
            onClick={() => setShowServers((v) => !v)}
          >
            Servers
          </Button>
          <Button variant="secondary" size="sm" onClick={() => fetchStatuses()}>
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Legend */}
      <div className="mb-4 flex items-center gap-4">
        {LEGEND.map((l) => (
          <div key={l.status} className="flex items-center gap-1.5">
            <div className={`h-3 w-3 rounded border ${l.color}`} />
            <span className="text-xs text-gray-500">{l.status}</span>
          </div>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : tables.length === 0 ? (
        <p className="text-sm text-gray-400">
          No tables found. Create a floor plan and add tables first.
        </p>
      ) : (
        <div className="flex gap-4">
          <div className="flex-1">
            <FloorPlanCanvas
              tables={tables}
              selectedId={currentSelected?.id ?? null}
              onSelectTable={(t) =>
                setSelectedTable(t as TableWithStatus | null)
              }
              onMoveTable={() => {}}
              disabled
              statusColors={statusColorMap}
            />
          </div>

          {/* Table Info Panel */}
          {currentSelected && (
            <div className="w-64 space-y-3 rounded-lg border border-gray-200 bg-white p-4">
              <h3 className="text-sm font-medium text-gray-900">
                {currentSelected.label}
              </h3>
              <div className="space-y-1 text-sm">
                <p>
                  <span className="text-gray-500">Status:</span>{" "}
                  <span className="font-medium capitalize">{currentSelected.status}</span>
                </p>
                <p>
                  <span className="text-gray-500">Capacity:</span>{" "}
                  {currentSelected.min_capacity}–{currentSelected.max_capacity}
                </p>
                {currentSelected.section && (
                  <p>
                    <span className="text-gray-500">Section:</span>{" "}
                    {currentSelected.section}
                  </p>
                )}
                {currentSelected.current_guest_name && (
                  <p>
                    <span className="text-gray-500">Guest:</span>{" "}
                    {currentSelected.current_guest_name}
                  </p>
                )}
                {currentSelected.current_party_size && (
                  <p>
                    <span className="text-gray-500">Party:</span>{" "}
                    {currentSelected.current_party_size}
                  </p>
                )}
                {currentSelected.next_reservation_time && (
                  <p>
                    <span className="text-gray-500">Next:</span>{" "}
                    {currentSelected.next_reservation_time.slice(0, 5)}
                  </p>
                )}
              </div>

              <div className="space-y-2 pt-2">
                {currentSelected.status === "available" && (
                  <>
                    <Button
                      size="sm"
                      className="w-full"
                      onClick={() => setShowAssign(true)}
                    >
                      Assign Reservation
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => handleHold(currentSelected.id)}
                    >
                      Hold Table
                    </Button>
                  </>
                )}
                {currentSelected.status === "held" && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={() => handleRelease(currentSelected.id)}
                  >
                    Release Hold
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Server Assignment Panel */}
      {showServers && tables.length > 0 && (
        <div className="mt-4">
          <ServerAssignmentPanel
            venueId={venue.id}
            date={date}
            sections={[...new Set(tables.map((t) => t.section).filter(Boolean) as string[])]}
          />
        </div>
      )}

      {currentSelected && (
        <AssignTableModal
          open={showAssign}
          onClose={() => setShowAssign(false)}
          venueId={venue.id}
          tableId={currentSelected.id}
          date={date}
          onAssigned={() => fetchStatuses()}
        />
      )}
    </div>
  );
}
