"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { formatDate, formatDateTime, cn } from "@/lib/utils";
import type { GuestDetail, Tag } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

export default function GuestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [guest, setGuest] = useState<GuestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [showAddTag, setShowAddTag] = useState(false);

  const fetchGuest = useCallback(async () => {
    try {
      const res = await api.get<GuestDetail>(`/guests/${id}`);
      setGuest(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load guest");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchGuest();
  }, [fetchGuest]);

  if (loading) return <p className="py-8 text-center text-sm text-gray-400">Loading...</p>;
  if (error || !guest) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-red-600">{error || "Guest not found"}</p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => router.push("/dashboard/guests")}>
          Back to Guests
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => router.push("/dashboard/guests")}
            className="text-sm text-gray-400 hover:text-gray-600"
          >
            &larr; Guests
          </button>
          <h1 className="text-xl font-semibold text-gray-900">
            {guest.first_name} {guest.last_name}
          </h1>
          <p className="text-sm text-gray-500">
            {guest.email || "No email"} {guest.phone ? ` | ${guest.phone}` : ""}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
          Edit Profile
        </Button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Visits" value={guest.total_visits} />
        <StatCard label="Last Visit" value={guest.last_visit_date ? formatDate(guest.last_visit_date.split("T")[0]) : "Never"} />
        <StatCard label="Avg Rating" value={guest.avg_overall_rating ? `${guest.avg_overall_rating}/5` : "N/A"} />
        <StatCard label="Member Since" value={formatDate(guest.created_at.split("T")[0])} />
      </div>

      {/* Profile details */}
      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Profile</h2>
          <ProfileRow label="Birthday" value={guest.birthday ? formatDate(guest.birthday) : null} />
          <ProfileRow label="Anniversary" value={guest.anniversary ? formatDate(guest.anniversary) : null} />
          <ProfileRow label="Dietary" value={guest.dietary_restrictions} />
          <ProfileRow label="Notes" value={guest.notes} />
        </div>

        {/* Tags */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">Tags</h2>
            <Button variant="ghost" size="sm" onClick={() => setShowAddTag(true)}>+ Add</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {guest.tags.length === 0 && (
              <p className="text-sm text-gray-400">No tags</p>
            )}
            {guest.tags.map((tag) => (
              <TagPill
                key={tag.id}
                tag={tag}
                onRemove={tag.is_auto ? undefined : async () => {
                  await api.delete(`/guests/${id}/tags/${tag.id}`);
                  fetchGuest();
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Visit timeline */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-900">Recent Visits</h2>
        {guest.visits.length === 0 ? (
          <p className="text-sm text-gray-400">No visits recorded</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {guest.visits.map((v) => (
              <div key={v.id} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">{v.venue_name}</p>
                  <p className="text-xs text-gray-500">{formatDateTime(v.visited_at)}</p>
                </div>
                <div className="text-right">
                  {v.spend_amount != null && (
                    <p className="text-sm text-gray-900">${Number(v.spend_amount).toFixed(2)}</p>
                  )}
                  {v.notes && <p className="text-xs text-gray-400">{v.notes}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Survey responses */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-900">Survey Responses</h2>
        {guest.surveys.length === 0 ? (
          <p className="text-sm text-gray-400">No survey responses</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {guest.surveys.map((s) => (
              <div key={s.id} className="py-2">
                <div className="flex items-center gap-3">
                  <Stars rating={s.overall_rating} />
                  <span className="text-xs text-gray-400">{formatDateTime(s.created_at)}</span>
                </div>
                {s.comment && <p className="mt-1 text-sm text-gray-600">{s.comment}</p>}
                <div className="mt-1 flex gap-3 text-xs text-gray-400">
                  {s.food_rating && <span>Food: {s.food_rating}/5</span>}
                  {s.service_rating && <span>Service: {s.service_rating}/5</span>}
                  {s.ambiance_rating && <span>Ambiance: {s.ambiance_rating}/5</span>}
                  {s.drinks_rating && <span>Drinks: {s.drinks_rating}/5</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editing && (
        <EditGuestModal
          guest={guest}
          onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); fetchGuest(); }}
        />
      )}

      {/* Add tag modal */}
      {showAddTag && (
        <AddTagModal
          guestId={id}
          existingTagIds={guest.tags.map((t) => t.id)}
          onClose={() => setShowAddTag(false)}
          onAdded={() => { setShowAddTag(false); fetchGuest(); }}
        />
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function ProfileRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900">{value || "---"}</span>
    </div>
  );
}

function TagPill({ tag, onRemove }: { tag: Tag; onRemove?: () => void }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        tag.is_auto
          ? "bg-blue-50 text-blue-700"
          : "bg-gray-100 text-gray-700"
      )}
      style={tag.color ? { backgroundColor: `${tag.color}20`, color: tag.color } : undefined}
    >
      {tag.name}
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-0.5 hover:opacity-70"
          aria-label={`Remove tag ${tag.name}`}
        >
          &times;
        </button>
      )}
    </span>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="text-sm" aria-label={`${rating} out of 5 stars`}>
      {"*".repeat(rating)}{"*".repeat(5 - rating).replace(/\*/g, "")}
      <span className="text-yellow-400">{"*".repeat(rating).replace(/\*/g, "\u2605")}</span>
      <span className="text-gray-300">{"\u2605".repeat(5 - rating)}</span>
    </span>
  );
}

function EditGuestModal({
  guest,
  onClose,
  onSaved,
}: {
  guest: GuestDetail;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const form = new FormData(e.currentTarget);
    const body: Record<string, string | null> = {};

    for (const field of ["first_name", "last_name", "email", "phone", "birthday", "anniversary", "dietary_restrictions", "notes"]) {
      const val = (form.get(field) as string)?.trim();
      if (val !== undefined) body[field] = val || null;
    }

    try {
      await api.patch(`/guests/${guest.id}`, body);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Edit Guest">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">First Name</label>
            <input name="first_name" defaultValue={guest.first_name} required className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Last Name</label>
            <input name="last_name" defaultValue={guest.last_name} required className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Email</label>
          <input name="email" type="email" defaultValue={guest.email || ""} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Phone</label>
          <input name="phone" defaultValue={guest.phone || ""} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Birthday</label>
            <input name="birthday" type="date" defaultValue={guest.birthday || ""} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Anniversary</label>
            <input name="anniversary" type="date" defaultValue={guest.anniversary || ""} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Dietary Restrictions</label>
          <textarea name="dietary_restrictions" defaultValue={guest.dietary_restrictions || ""} rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-700">Notes</label>
          <textarea name="notes" defaultValue={guest.notes || ""} rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function AddTagModal({
  guestId,
  existingTagIds,
  onClose,
  onAdded,
}: {
  guestId: string;
  existingTagIds: string[];
  onClose: () => void;
  onAdded: () => void;
}) {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Tag[]>("/tags?is_auto=false&per_page=100")
      .then((res) => setTags(res.data.filter((t) => !existingTagIds.includes(t.id))))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [existingTagIds]);

  const handleAdd = async (tagId: string) => {
    await api.post(`/guests/${guestId}/tags`, { tag_id: tagId });
    onAdded();
  };

  return (
    <Modal open onClose={onClose} title="Add Tag">
      {loading ? (
        <p className="py-4 text-center text-sm text-gray-400">Loading tags...</p>
      ) : tags.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-400">No available tags to add</p>
      ) : (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {tags.map((tag) => (
            <button
              key={tag.id}
              onClick={() => handleAdd(tag.id)}
              className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-gray-50"
            >
              <span className="font-medium text-gray-900">{tag.name}</span>
              {tag.description && (
                <span className="text-xs text-gray-400">{tag.description}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </Modal>
  );
}
