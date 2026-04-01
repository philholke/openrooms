"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { minutesElapsed } from "@/lib/utils";
import type { WaitlistEntry } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";

export default function WaitlistPage() {
  const { current: venue } = useVenue();
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const fetchEntries = useCallback(async (signal?: AbortSignal) => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<WaitlistEntry[]>(
        `/venues/${venue.id}/waitlist?active_only=true`
      );
      if (signal?.aborted) return;
      setEntries(res.data);
    } catch (err) {
      if (signal?.aborted) return;
      setError(err instanceof Error ? err.message : "Failed to load waitlist");
      setEntries([]);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [venue]);

  useEffect(() => {
    const controller = new AbortController();
    let delay = 15_000;
    let timer: ReturnType<typeof setTimeout>;
    let mounted = true;

    const poll = async () => {
      if (!mounted) return;
      try {
        await fetchEntries(controller.signal);
        delay = 15_000; // reset on success
      } catch {
        delay = Math.min(delay * 1.5, 300_000); // backoff, cap 5 min
      }
      if (mounted && !controller.signal.aborted) {
        timer = setTimeout(poll, delay);
      }
    };

    fetchEntries(controller.signal);
    timer = setTimeout(poll, delay);
    return () => {
      mounted = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [venue?.id, fetchEntries]);

  const [actionError, setActionError] = useState<string | null>(null);

  const handleStatusChange = async (
    entryId: string,
    newStatus: string
  ) => {
    setActionError(null);
    try {
      await api.patch(`/waitlist/${entryId}`, { status: newStatus });
      fetchEntries();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update");
    }
  };

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected.</p>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Waitlist</h1>
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={() => fetchEntries()}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowAdd(true)}>
            + Add to Waitlist
          </Button>
        </div>
      </div>

      {/* Errors */}
      {(error || actionError) && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error || actionError}
        </div>
      )}

      {/* List */}
      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          Waitlist is empty.
        </p>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => {
            const elapsed = minutesElapsed(entry.check_in_time);
            const guest = entry.guest;

            return (
              <div
                key={entry.id}
                className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3"
              >
                <div className="flex items-center gap-4">
                  {/* Party size circle */}
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-sm font-semibold text-gray-700">
                    {entry.party_size}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {guest
                        ? `${guest.first_name} ${guest.last_name}`
                        : "Walk-in"}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span>
                        {elapsed} min waiting
                        {entry.quoted_wait_minutes
                          ? ` / ${entry.quoted_wait_minutes} min quoted`
                          : ""}
                      </span>
                      {guest?.phone && <span>&middot; {guest.phone}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <StatusBadge status={entry.status} />
                  {entry.status === "waiting" && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() =>
                          handleStatusChange(entry.id, "notified")
                        }
                      >
                        Notify
                      </Button>
                      <Button
                        size="sm"
                        onClick={() =>
                          handleStatusChange(entry.id, "seated")
                        }
                      >
                        Seat
                      </Button>
                    </>
                  )}
                  {entry.status === "notified" && (
                    <Button
                      size="sm"
                      onClick={() =>
                        handleStatusChange(entry.id, "seated")
                      }
                    >
                      Seat
                    </Button>
                  )}
                  {(entry.status === "waiting" ||
                    entry.status === "notified") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        handleStatusChange(entry.id, "no_show")
                      }
                    >
                      No Show
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-gray-400">
        {entries.length} active entr{entries.length !== 1 ? "ies" : "y"}
      </p>

      {/* Add to Waitlist Modal */}
      <AddToWaitlistModal
        open={showAdd}
        onClose={() => setShowAdd(false)}
        venueId={venue.id}
        onAdded={fetchEntries}
      />
    </div>
  );
}

// ─── Add to Waitlist Modal ──────────────────────────────────────────────

function AddToWaitlistModal({
  open,
  onClose,
  venueId,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  venueId: string;
  onAdded: () => void;
}) {
  const initialForm = {
    first_name: "",
    last_name: "",
    phone: "",
    party_size: 2,
    quoted_wait_minutes: "",
    notes: "",
  };
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Reset form state when modal opens
  useEffect(() => {
    if (open) {
      setForm(initialForm);
      setError("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post(`/venues/${venueId}/waitlist`, {
        party_size: form.party_size,
        guest: {
          first_name: form.first_name,
          last_name: form.last_name,
          phone: form.phone || null,
        },
        quoted_wait_minutes: form.quoted_wait_minutes
          ? parseInt(form.quoted_wait_minutes)
          : null,
        notes: form.notes || null,
      });
      onAdded();
      onClose();
      // Reset form
      setForm({
        first_name: "",
        last_name: "",
        phone: "",
        party_size: 2,
        quoted_wait_minutes: "",
        notes: "",
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Add to Waitlist">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="First Name"
            value={form.first_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, first_name: e.target.value }))
            }
            required
          />
          <Input
            label="Last Name"
            value={form.last_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, last_name: e.target.value }))
            }
            required
          />
        </div>
        <Input
          label="Phone"
          type="tel"
          value={form.phone}
          onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
        />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">
            Party Size
          </label>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Party size">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={form.party_size === n}
                aria-label={`${n} guest${n !== 1 ? "s" : ""}`}
                onClick={() => setForm((f) => ({ ...f, party_size: n }))}
                className={`h-9 w-9 rounded-lg text-sm font-medium transition-colors ${
                  form.party_size === n
                    ? "bg-gray-900 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <Input
          label="Quoted Wait (minutes)"
          type="number"
          value={form.quoted_wait_minutes}
          onChange={(e) =>
            setForm((f) => ({ ...f, quoted_wait_minutes: e.target.value }))
          }
          placeholder="15"
          min="0"
        />
        <Input
          label="Notes"
          value={form.notes}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          placeholder="High chair needed, birthday..."
        />
        <Button
          type="submit"
          className="w-full"
          disabled={loading || !form.first_name || !form.last_name}
        >
          {loading ? "Adding..." : "Add to Waitlist"}
        </Button>
      </form>
    </Modal>
  );
}
