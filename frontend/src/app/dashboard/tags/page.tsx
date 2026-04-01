"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Tag, AutoTagRule, AutoTagConditions, BulkEvaluateResult } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

export default function TagsPage() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"manual" | "auto">("manual");
  const [showCreate, setShowCreate] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editingRule, setEditingRule] = useState<Tag | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<BulkEvaluateResult | null>(null);

  const fetchTags = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Tag[]>(`/tags?is_auto=${tab === "auto"}&per_page=100`);
      setTags(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tags");
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => { fetchTags(); }, [fetchTags]);

  const handleDelete = async (tag: Tag) => {
    if (!confirm(`Delete tag "${tag.name}"? This removes it from all guests.`)) return;
    try {
      await api.delete(`/tags/${tag.id}`);
      fetchTags();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete tag");
    }
  };

  const handleBulkEvaluate = async () => {
    setEvaluating(true);
    setEvalResult(null);
    try {
      const res = await api.post<BulkEvaluateResult>("/tags/evaluate");
      setEvalResult(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Tags</h1>
        <div className="flex gap-2">
          {tab === "auto" && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleBulkEvaluate}
              disabled={evaluating}
            >
              {evaluating ? "Evaluating..." : "Run All Rules"}
            </Button>
          )}
          <Button size="sm" onClick={() => setShowCreate(true)}>
            + Create Tag
          </Button>
        </div>
      </div>

      {/* Eval result toast */}
      {evalResult && (
        <div className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
          Evaluated {evalResult.guests_evaluated} guests: {evalResult.tags_applied} tags applied, {evalResult.tags_removed} removed.
          <button className="ml-2 underline" onClick={() => setEvalResult(null)}>Dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200" role="tablist">
        {(["manual", "auto"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px capitalize",
              tab === t
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            {t === "manual" ? "Manual Tags" : "Auto Tags"}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Tag grid */}
      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">Loading...</p>
      ) : tags.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          No {tab} tags yet. Create one to get started.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {tags.map((tag) => (
            <div
              key={tag.id}
              className="rounded-xl border border-gray-200 bg-white p-4 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {tag.color && (
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: tag.color }}
                    />
                  )}
                  <span className="font-medium text-gray-900">{tag.name}</span>
                </div>
                <div className="flex gap-1">
                  {tag.is_auto && (
                    <Button variant="ghost" size="sm" onClick={() => setEditingRule(tag)}>
                      Rule
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => setEditingTag(tag)}>
                    Edit
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(tag)}>
                    Delete
                  </Button>
                </div>
              </div>
              {tag.description && (
                <p className="text-xs text-gray-500">{tag.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit tag modal */}
      {(showCreate || editingTag) && (
        <TagFormModal
          tag={editingTag}
          isAutoTab={tab === "auto"}
          onClose={() => { setShowCreate(false); setEditingTag(null); }}
          onSaved={() => { setShowCreate(false); setEditingTag(null); fetchTags(); }}
        />
      )}

      {/* Rule editor modal */}
      {editingRule && (
        <RuleEditorModal
          tag={editingRule}
          onClose={() => setEditingRule(null)}
          onSaved={() => { setEditingRule(null); }}
        />
      )}
    </div>
  );
}

function TagFormModal({
  tag,
  isAutoTab,
  onClose,
  onSaved,
}: {
  tag: Tag | null;
  isAutoTab: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = tag !== null;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const form = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      name: form.get("name"),
      color: (form.get("color") as string) || null,
      description: (form.get("description") as string) || null,
    };
    if (!isEdit) {
      body.is_auto = isAutoTab;
    }

    try {
      if (isEdit) {
        await api.patch(`/tags/${tag.id}`, body);
      } else {
        await api.post("/tags", body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save tag");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open onClose={onClose} title={isEdit ? "Edit Tag" : "Create Tag"}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Name *</label>
          <input name="name" required defaultValue={tag?.name || ""} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Color</label>
          <input name="color" type="color" defaultValue={tag?.color || "#6B7280"} className="h-10 w-20 rounded border border-gray-300" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea name="description" defaultValue={tag?.description || ""} rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : isEdit ? "Save" : "Create"}</Button>
        </div>
      </form>
    </Modal>
  );
}

const CONDITION_LABELS: Record<string, string> = {
  visit_count_gte: "Visit count >=",
  visit_count_lte: "Visit count <=",
  last_visit_within_days: "Last visit within (days)",
  last_visit_not_within_days: "Not visited in (days)",
  total_spend_gte: "Total spend >= (cents)",
  avg_rating_gte: "Avg rating >=",
  avg_rating_lte: "Avg rating <=",
  has_tag: "Has tag",
  not_has_tag: "Does not have tag",
};

function RuleEditorModal({
  tag,
  onClose,
  onSaved,
}: {
  tag: Tag;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [conditions, setConditions] = useState<AutoTagConditions>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<AutoTagRule>(`/tags/${tag.id}/rule`)
      .then((res) => setConditions(res.data.conditions))
      .catch(() => {}) // 404 = no rule yet
      .finally(() => setLoading(false));
  }, [tag.id]);

  const updateCondition = (key: string, value: string) => {
    setConditions((prev) => {
      const next = { ...prev };
      if (value === "") {
        delete (next as Record<string, unknown>)[key];
      } else if (key === "has_tag" || key === "not_has_tag") {
        (next as Record<string, unknown>)[key] = value;
      } else {
        const num = Number(value);
        if (!isNaN(num)) (next as Record<string, unknown>)[key] = num;
      }
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.put(`/tags/${tag.id}/rule`, { conditions });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save rule");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Modal open onClose={onClose} title={`Rule: ${tag.name}`}><p className="py-4 text-center text-sm text-gray-400">Loading...</p></Modal>;

  return (
    <Modal open onClose={onClose} title={`Rule: ${tag.name}`} className="max-w-xl">
      <div className="space-y-3">
        <p className="text-xs text-gray-500">All conditions are AND-combined. Leave empty to skip.</p>
        {Object.entries(CONDITION_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-3">
            <label className="w-48 text-sm text-gray-700">{label}</label>
            <input
              type={key === "has_tag" || key === "not_has_tag" ? "text" : "number"}
              step={key.includes("rating") ? "0.1" : "1"}
              value={(conditions as Record<string, unknown>)[key] ?? ""}
              onChange={(e) => updateCondition(key, e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              placeholder="Not set"
            />
          </div>
        ))}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Rule"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
