"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Table } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

const SHAPE_OPTIONS = [
  { value: "rectangle", label: "Rectangle" },
  { value: "circle", label: "Circle" },
  { value: "square", label: "Square" },
];

interface TablePropertiesPanelProps {
  table: Table;
  onUpdated: () => void;
  onDeleted: () => void;
}

export function TablePropertiesPanel({
  table,
  onUpdated,
  onDeleted,
}: TablePropertiesPanelProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [label, setLabel] = useState(table.label);
  const [minCap, setMinCap] = useState(String(table.min_capacity));
  const [maxCap, setMaxCap] = useState(String(table.max_capacity));
  const [section, setSection] = useState(table.section || "");
  const [shape, setShape] = useState(table.shape);

  // Re-sync when a different table is selected
  if (table.label !== label && !saving) {
    setLabel(table.label);
    setMinCap(String(table.min_capacity));
    setMaxCap(String(table.max_capacity));
    setSection(table.section || "");
    setShape(table.shape);
    setError("");
  }

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await api.patch(`/tables/${table.id}`, {
        label: label.trim(),
        min_capacity: parseInt(minCap, 10),
        max_capacity: parseInt(maxCap, 10),
        section: section.trim() || null,
        shape,
      });
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/tables/${table.id}`);
      onDeleted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="w-64 space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-medium text-gray-900">Table Properties</h3>

      <Input
        label="Label"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        maxLength={100}
      />
      <div className="grid grid-cols-2 gap-2">
        <Input
          label="Min Cap."
          type="number"
          value={minCap}
          onChange={(e) => setMinCap(e.target.value)}
          min={1}
        />
        <Input
          label="Max Cap."
          type="number"
          value={maxCap}
          onChange={(e) => setMaxCap(e.target.value)}
          min={1}
        />
      </div>
      <Input
        label="Section"
        value={section}
        onChange={(e) => setSection(e.target.value)}
        maxLength={100}
      />
      <Select
        label="Shape"
        value={shape}
        onChange={(e) => setShape(e.target.value)}
        options={SHAPE_OPTIONS}
      />

      {error && (
        <div role="alert" className="text-xs text-red-600">{error}</div>
      )}

      <div className="flex gap-2">
        <Button size="sm" onClick={handleSave} disabled={saving || !label.trim()}>
          {saving ? "Saving..." : "Save"}
        </Button>
        <Button variant="danger" size="sm" onClick={handleDelete}>
          Delete
        </Button>
      </div>
    </div>
  );
}
