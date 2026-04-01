"use client";

import { useCallback, useRef, useState } from "react";
import type { Table } from "@/lib/types";
import { CANVAS_HEIGHT, CANVAS_WIDTH, screenToSvg } from "@/lib/floor-plan-utils";
import { TableShape } from "./TableShape";

interface FloorPlanCanvasProps {
  tables: Table[];
  selectedId: string | null;
  onSelectTable: (table: Table | null) => void;
  onMoveTable: (tableId: string, x: number, y: number) => void;
  disabled?: boolean;
  statusColors?: Record<string, { fill: string; stroke: string }>;
  children?: React.ReactNode;
}

export function FloorPlanCanvas({
  tables,
  selectedId,
  onSelectTable,
  onMoveTable,
  disabled = false,
  statusColors,
  children,
}: FloorPlanCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const panOffset = useRef({ x: 0, y: 0 });

  const viewWidth = CANVAS_WIDTH / zoom;
  const viewHeight = CANVAS_HEIGHT / zoom;

  // Pan: pointer down on background
  const handleBgPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (disabled) return;
      // Only start panning if clicking the background (not a table)
      if (e.target !== svgRef.current) return;
      onSelectTable(null);
      panning.current = true;
      panStart.current = { x: e.clientX, y: e.clientY };
      panOffset.current = { ...pan };
      (e.target as SVGElement).setPointerCapture(e.pointerId);
    },
    [disabled, onSelectTable, pan],
  );

  const handleBgPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!panning.current || !svgRef.current) return;
      const ctm = svgRef.current.getScreenCTM();
      if (!ctm) return;
      const scale = ctm.a; // current pixel-to-SVG scale
      const dx = (e.clientX - panStart.current.x) / scale;
      const dy = (e.clientY - panStart.current.y) / scale;
      setPan({
        x: panOffset.current.x - dx,
        y: panOffset.current.y - dy,
      });
    },
    [],
  );

  const handleBgPointerUp = useCallback(() => {
    panning.current = false;
  }, []);

  // Zoom: scroll wheel
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((prev) => {
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      return Math.min(4, Math.max(0.25, prev * factor));
    });
  }, []);

  return (
    <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-white">
      {/* Zoom indicator */}
      <div className="absolute right-3 top-3 z-10 rounded bg-white/80 px-2 py-1 text-xs text-gray-500 shadow-sm">
        {Math.round(zoom * 100)}%
      </div>
      <svg
        ref={svgRef}
        viewBox={`${pan.x} ${pan.y} ${viewWidth} ${viewHeight}`}
        className="h-[600px] w-full"
        onPointerDown={handleBgPointerDown}
        onPointerMove={handleBgPointerMove}
        onPointerUp={handleBgPointerUp}
        onWheel={handleWheel}
        style={{ touchAction: "none" }}
      >
        {/* Grid pattern */}
        <defs>
          <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#f3f4f6" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect
          x={pan.x - 1000}
          y={pan.y - 1000}
          width={viewWidth + 2000}
          height={viewHeight + 2000}
          fill="url(#grid)"
        />

        {/* Table shapes */}
        {tables.map((table) => (
          <TableShape
            key={table.id}
            table={table}
            selected={table.id === selectedId}
            onSelect={(t) => onSelectTable(t)}
            onMove={onMoveTable}
            disabled={disabled}
            statusColor={statusColors?.[table.id]}
          />
        ))}

        {children}
      </svg>
    </div>
  );
}
