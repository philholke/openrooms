"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import type { FloorPlan } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

function CreateFloorPlanModal({
  open,
  onClose,
  venueId,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  venueId: string;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setName("");
      setError("");
    }
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      await api.post(`/venues/${venueId}/floor-plans`, { name: name.trim() });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create floor plan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="New Floor Plan">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Main Dining, Patio, Bar"
          required
          maxLength={255}
        />
        {error && (
          <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading || !name.trim()}>
            {loading ? "Creating..." : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function FloorPlansPage() {
  const { current: venue } = useVenue();
  const router = useRouter();
  const [floorPlans, setFloorPlans] = useState<FloorPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchFloorPlans = useCallback(async () => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<FloorPlan[]>(`/venues/${venue.id}/floor-plans`);
      setFloorPlans(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load floor plans");
    } finally {
      setLoading(false);
    }
  }, [venue]);

  useEffect(() => {
    fetchFloorPlans();
  }, [fetchFloorPlans]);

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/floor-plans/${id}`);
      fetchFloorPlans();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete floor plan");
    }
  };

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected</p>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Floor Plans</h1>
        <Button onClick={() => setShowCreate(true)}>New Floor Plan</Button>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : floorPlans.length === 0 ? (
        <p className="text-sm text-gray-400">
          No floor plans yet. Create one to get started.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {floorPlans.map((fp) => (
            <Card
              key={fp.id}
              onClick={() => router.push(`/dashboard/floor-plans/${fp.id}`)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{fp.name}</h3>
                  <p className="text-xs text-gray-400">
                    Created {new Date(fp.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(fp.id);
                  }}
                >
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateFloorPlanModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        venueId={venue.id}
        onCreated={fetchFloorPlans}
      />
    </div>
  );
}
