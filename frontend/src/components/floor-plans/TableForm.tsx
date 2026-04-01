"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Table } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";

interface TableFormProps {
  open: boolean;
  onClose: () => void;
  floorPlanId: string;
  table?: Table | null;
  onSaved: () => void;
}

const SHAPE_OPTIONS = [
  { value: "rectangle", label: "Rectangle" },
  { value: "circle", label: "Circle" },
  { value: "square", label: "Square" },
];

const initialForm = {
  label: "",
  min_capacity: "1",
  max_capacity: "4",
  section: "",
  shape: "rectangle",
};

export function TableForm({ open, onClose, floorPlanId, table, onSaved }: TableFormProps) {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const isEdit = !!table;

  useEffect(() => {
    if (open) {
      if (table) {
        setForm({
          label: table.label,
          min_capacity: String(table.min_capacity),
          max_capacity: String(table.max_capacity),
          section: table.section || "",
          shape: table.shape,
        });
      } else {
        setForm(initialForm);
      }
      setError("");
    }
  }, [open, table]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const min = parseInt(form.min_capacity, 10);
    const max = parseInt(form.max_capacity, 10);
    if (isNaN(min) || isNaN(max) || min < 1 || max < 1) {
      setError("Capacity must be at least 1");
      return;
    }
    if (min > max) {
      setError("Min capacity must be less than or equal to max capacity");
      return;
    }

    setLoading(true);
    setError("");

    const payload = {
      label: form.label.trim(),
      min_capacity: min,
      max_capacity: max,
      section: form.section.trim() || null,
      shape: form.shape,
    };

    try {
      if (isEdit) {
        await api.patch(`/tables/${table.id}`, payload);
      } else {
        await api.post(`/floor-plans/${floorPlanId}/tables`, payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save table");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? "Edit Table" : "Add Table"}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Label"
          value={form.label}
          onChange={(e) => setForm({ ...form, label: e.target.value })}
          placeholder="e.g. T1, Bar 3, Patio 12"
          required
          maxLength={100}
        />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Min Capacity"
            type="number"
            value={form.min_capacity}
            onChange={(e) => setForm({ ...form, min_capacity: e.target.value })}
            min={1}
            required
          />
          <Input
            label="Max Capacity"
            type="number"
            value={form.max_capacity}
            onChange={(e) => setForm({ ...form, max_capacity: e.target.value })}
            min={1}
            required
          />
        </div>
        <Input
          label="Section"
          value={form.section}
          onChange={(e) => setForm({ ...form, section: e.target.value })}
          placeholder="e.g. Patio, Bar, Main"
          maxLength={100}
        />
        <Select
          label="Shape"
          value={form.shape}
          onChange={(e) => setForm({ ...form, shape: e.target.value })}
          options={SHAPE_OPTIONS}
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
          <Button type="submit" disabled={loading || !form.label.trim()}>
            {loading ? "Saving..." : isEdit ? "Save Changes" : "Add Table"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
