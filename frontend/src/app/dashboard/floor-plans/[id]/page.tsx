"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import type { FloorPlan, Table } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { TableForm } from "@/components/floor-plans/TableForm";
import { FloorPlanCanvas } from "@/components/floor-plans/FloorPlanCanvas";
import { TablePropertiesPanel } from "@/components/floor-plans/TablePropertiesPanel";
import { DEFAULT_TABLE_POSITION } from "@/lib/floor-plan-utils";

type ViewMode = "canvas" | "list";

export default function FloorPlanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { current: venue } = useVenue();

  const [floorPlan, setFloorPlan] = useState<FloorPlan | null>(null);
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("canvas");

  // Rename state
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");

  // Table form state
  const [showTableForm, setShowTableForm] = useState(false);
  const [editingTable, setEditingTable] = useState<Table | null>(null);

  // Canvas state
  const [selectedTable, setSelectedTable] = useState<Table | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const movedPositions = useRef<Map<string, { x: number; y: number }>>(new Map());

  const fetchData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [fpRes, tablesRes] = await Promise.all([
        api.get<FloorPlan>(`/floor-plans/${id}`),
        api.get<Table[]>(`/floor-plans/${id}/tables`),
      ]);
      setFloorPlan(fpRes.data);
      setTables(tablesRes.data);
      setNameValue(fpRes.data.name);
      movedPositions.current.clear();
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load floor plan");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRename = async () => {
    if (!nameValue.trim() || !floorPlan) return;
    try {
      const res = await api.patch<FloorPlan>(`/floor-plans/${id}`, {
        name: nameValue.trim(),
      });
      setFloorPlan(res.data);
      setEditingName(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to rename");
    }
  };

  const handleDeleteTable = async (tableId: string) => {
    try {
      await api.delete(`/tables/${tableId}`);
      if (selectedTable?.id === tableId) setSelectedTable(null);
      fetchData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete table");
    }
  };

  // Canvas: move table locally (optimistic update for drag)
  const handleMoveTable = useCallback((tableId: string, x: number, y: number) => {
    movedPositions.current.set(tableId, { x, y });
    setTables((prev) =>
      prev.map((t) =>
        t.id === tableId ? { ...t, x_position: x, y_position: y } : t,
      ),
    );
    setDirty(true);
  }, []);

  // Canvas: save all moved positions
  const handleSaveLayout = async () => {
    setSaving(true);
    setError(null);
    try {
      const promises = Array.from(movedPositions.current.entries()).map(
        ([tableId, pos]) =>
          api.patch(`/tables/${tableId}`, {
            x_position: pos.x,
            y_position: pos.y,
          }),
      );
      await Promise.all(promises);
      movedPositions.current.clear();
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save layout");
    } finally {
      setSaving(false);
    }
  };

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected</p>;
  }

  if (loading) {
    return <p className="text-sm text-gray-400">Loading...</p>;
  }

  if (!floorPlan) {
    return <p className="text-sm text-gray-400">Floor plan not found</p>;
  }

  // Keep selectedTable in sync with tables state
  const currentSelected = selectedTable
    ? tables.find((t) => t.id === selectedTable.id) ?? null
    : null;

  // Group tables by section for list view
  const sections = new Map<string, Table[]>();
  for (const table of tables) {
    const key = table.section || "Unassigned";
    if (!sections.has(key)) sections.set(key, []);
    sections.get(key)!.push(table);
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/floor-plans")}>
          &larr; Back
        </Button>
        {editingName ? (
          <div className="flex items-center gap-2">
            <Input
              value={nameValue}
              onChange={(e) => setNameValue(e.target.value)}
              maxLength={255}
              className="w-64"
            />
            <Button size="sm" onClick={handleRename}>Save</Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setNameValue(floorPlan.name);
                setEditingName(false);
              }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <h1
            className="cursor-pointer text-xl font-semibold text-gray-900 hover:text-gray-600"
            onClick={() => setEditingName(true)}
            title="Click to rename"
          >
            {floorPlan.name}
          </h1>
        )}
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Toolbar */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium text-gray-900">
            Tables ({tables.length})
          </h2>
          <div className="ml-4 flex rounded-lg border border-gray-200">
            <button
              className={`px-3 py-1 text-xs font-medium ${
                viewMode === "canvas"
                  ? "bg-gray-900 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              } rounded-l-lg`}
              onClick={() => setViewMode("canvas")}
            >
              Canvas
            </button>
            <button
              className={`px-3 py-1 text-xs font-medium ${
                viewMode === "list"
                  ? "bg-gray-900 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              } rounded-r-lg`}
              onClick={() => setViewMode("list")}
            >
              List
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {viewMode === "canvas" && dirty && (
            <Button onClick={handleSaveLayout} disabled={saving}>
              {saving ? "Saving..." : "Save Layout"}
            </Button>
          )}
          <Button
            onClick={() => {
              setEditingTable(null);
              setShowTableForm(true);
            }}
          >
            Add Table
          </Button>
        </div>
      </div>

      {tables.length === 0 ? (
        <p className="text-sm text-gray-400">
          No tables yet. Add tables to this floor plan.
        </p>
      ) : viewMode === "canvas" ? (
        /* ─── Canvas View ─── */
        <div className="flex gap-4">
          <div className="flex-1">
            <FloorPlanCanvas
              tables={tables}
              selectedId={currentSelected?.id ?? null}
              onSelectTable={(t) => setSelectedTable(t)}
              onMoveTable={handleMoveTable}
            />
          </div>
          {currentSelected && (
            <TablePropertiesPanel
              key={currentSelected.id}
              table={currentSelected}
              onUpdated={fetchData}
              onDeleted={() => {
                setSelectedTable(null);
                fetchData();
              }}
            />
          )}
        </div>
      ) : (
        /* ─── List View ─── */
        <div className="space-y-6">
          {Array.from(sections.entries()).map(([section, sectionTables]) => (
            <div key={section}>
              <h3 className="mb-2 text-sm font-medium text-gray-500">{section}</h3>
              <div className="overflow-hidden rounded-lg border border-gray-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 font-medium text-gray-600">Label</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Capacity</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Shape</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Position</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {sectionTables.map((t) => (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium">{t.label}</td>
                        <td className="px-4 py-2 text-gray-600">
                          {t.min_capacity === t.max_capacity
                            ? t.max_capacity
                            : `${t.min_capacity}–${t.max_capacity}`}
                        </td>
                        <td className="px-4 py-2 capitalize text-gray-600">{t.shape}</td>
                        <td className="px-4 py-2 text-gray-400">
                          {t.x_position != null && t.y_position != null
                            ? `(${t.x_position.toFixed(0)}, ${t.y_position.toFixed(0)})`
                            : "—"}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                setEditingTable(t);
                                setShowTableForm(true);
                              }}
                            >
                              Edit
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => handleDeleteTable(t.id)}
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      <TableForm
        open={showTableForm}
        onClose={() => {
          setShowTableForm(false);
          setEditingTable(null);
        }}
        floorPlanId={id}
        table={editingTable}
        onSaved={fetchData}
      />
    </div>
  );
}
