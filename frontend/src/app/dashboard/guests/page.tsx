"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { cn } from "@/lib/utils";
import type { GuestListItem, Tag } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

export default function GuestsPage() {
  const router = useRouter();
  const { current: venue } = useVenue();
  const [guests, setGuests] = useState<GuestListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState<string>("");
  const [tags, setTags] = useState<Tag[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Fetch tags for filter dropdown
  useEffect(() => {
    api.get<Tag[]>("/tags?per_page=100").then((res) => setTags(res.data)).catch(() => {});
  }, []);

  const fetchGuests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), per_page: "25" });
      if (search) params.set("search", search);
      if (tagFilter) params.set("tag_id", tagFilter);
      const res = await api.get<GuestListItem[]>(`/guests?${params}`);
      setGuests(res.data);
      setTotal(res.meta?.total ?? res.data.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load guests");
      setGuests([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, tagFilter]);

  useEffect(() => {
    fetchGuests();
  }, [fetchGuests]);

  const handleSearchChange = (value: string) => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
      setPage(1);
    }, 300);
  };

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected.</p>;
  }

  const totalPages = Math.ceil(total / 25);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Guests</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          + Add Guest
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search name or email..."
          defaultValue={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-64 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        />
        <select
          value={tagFilter}
          onChange={(e) => { setTagFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All tags</option>
          {tags.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <Button variant="secondary" size="sm" onClick={fetchGuests}>
          Refresh
        </Button>
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
      ) : guests.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          {search || tagFilter ? "No guests match your filters." : "No guests yet."}
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-4 py-3 font-medium text-gray-500">Name</th>
                <th className="px-4 py-3 font-medium text-gray-500">Email</th>
                <th className="px-4 py-3 font-medium text-gray-500">Phone</th>
                <th className="px-4 py-3 font-medium text-gray-500">Visits</th>
                <th className="px-4 py-3 font-medium text-gray-500">Tags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {guests.map((g) => (
                <tr
                  key={g.id}
                  onClick={() => router.push(`/dashboard/guests/${g.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      router.push(`/dashboard/guests/${g.id}`);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Guest ${g.first_name} ${g.last_name}`}
                  className="cursor-pointer hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
                >
                  <td className="px-4 py-3 font-medium">
                    {g.first_name} {g.last_name}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{g.email || "---"}</td>
                  <td className="px-4 py-3 text-gray-500">{g.phone || "---"}</td>
                  <td className="px-4 py-3">{g.total_visits}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {g.tag_names.map((t) => (
                        <span
                          key={t}
                          className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          {total} guest{total !== 1 ? "s" : ""}
        </p>
        {totalPages > 1 && (
          <div className="flex gap-1">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Prev
            </Button>
            <span className="px-3 py-1.5 text-sm text-gray-500">
              {page} / {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Create guest modal */}
      <CreateGuestModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(id) => {
          setShowCreate(false);
          router.push(`/dashboard/guests/${id}`);
        }}
      />
    </div>
  );
}

function CreateGuestModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const form = new FormData(e.currentTarget);
    const body: Record<string, string | null> = {
      first_name: form.get("first_name") as string,
      last_name: form.get("last_name") as string,
    };
    const email = (form.get("email") as string)?.trim();
    const phone = (form.get("phone") as string)?.trim();
    if (email) body.email = email;
    if (phone) body.phone = phone;

    try {
      const res = await api.post<{ id: string }>("/guests", body);
      onCreated(res.data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create guest");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Add Guest">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">First Name *</label>
            <input name="first_name" required className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Last Name *</label>
            <input name="last_name" required className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input name="email" type="email" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Phone</label>
          <input name="phone" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Add Guest"}</Button>
        </div>
      </form>
    </Modal>
  );
}
