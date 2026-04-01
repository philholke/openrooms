"use client";

import { useCallback, useRef } from "react";
import type { Table } from "@/lib/types";
import { getTableDimensions, screenToSvg, snapToGrid } from "@/lib/floor-plan-utils";

interface TableShapeProps {
  table: Table;
  selected: boolean;
  onSelect: (table: Table) => void;
  onMove: (tableId: string, x: number, y: number) => void;
  disabled?: boolean;
  statusColor?: { fill: string; stroke: string };
}

export function TableShape({
  table,
  selected,
  onSelect,
  onMove,
  disabled = false,
  statusColor,
}: TableShapeProps) {
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });

  const { width, height } = getTableDimensions(table.shape, table.max_capacity);
  const x = table.x_position ?? 0;
  const y = table.y_position ?? 0;

  const fill = statusColor?.fill ?? (selected ? "#e0e7ff" : "#f9fafb");
  const stroke = statusColor?.stroke ?? (selected ? "#4f46e5" : "#d1d5db");

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (disabled) return;
      e.stopPropagation();
      onSelect(table);

      const svg = (e.target as SVGElement).ownerSVGElement;
      if (!svg) return;

      const svgPt = screenToSvg(svg, e.clientX, e.clientY);
      offset.current = { x: svgPt.x - x, y: svgPt.y - y };
      dragging.current = true;
      (e.target as SVGElement).setPointerCapture(e.pointerId);
    },
    [disabled, onSelect, table, x, y],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current) return;
      const svg = (e.target as SVGElement).ownerSVGElement;
      if (!svg) return;

      const svgPt = screenToSvg(svg, e.clientX, e.clientY);
      const newX = snapToGrid(svgPt.x - offset.current.x);
      const newY = snapToGrid(svgPt.y - offset.current.y);
      onMove(table.id, newX, newY);
    },
    [onMove, table.id],
  );

  const handlePointerUp = useCallback(() => {
    dragging.current = false;
  }, []);

  const shapeProps = {
    onPointerDown: handlePointerDown,
    onPointerMove: handlePointerMove,
    onPointerUp: handlePointerUp,
    style: { cursor: disabled ? "default" : "grab", touchAction: "none" as const },
  };

  // Capacity label
  const capacityLabel =
    table.min_capacity === table.max_capacity
      ? `${table.max_capacity}`
      : `${table.min_capacity}-${table.max_capacity}`;

  return (
    <g
      transform={`translate(${x}, ${y})`}
      role="button"
      aria-label={`Table ${table.label}, seats ${capacityLabel}`}
    >
      {table.shape === "circle" ? (
        <ellipse
          cx={width / 2}
          cy={height / 2}
          rx={width / 2}
          ry={height / 2}
          fill={fill}
          stroke={stroke}
          strokeWidth={selected ? 2.5 : 1.5}
          {...shapeProps}
        />
      ) : (
        <rect
          width={width}
          height={height}
          rx={table.shape === "square" ? 4 : 8}
          fill={fill}
          stroke={stroke}
          strokeWidth={selected ? 2.5 : 1.5}
          {...shapeProps}
        />
      )}
      {/* Table label */}
      <text
        x={width / 2}
        y={height / 2 - 6}
        textAnchor="middle"
        dominantBaseline="central"
        className="pointer-events-none select-none fill-gray-800 text-xs font-semibold"
        style={{ fontSize: 12 }}
      >
        {table.label}
      </text>
      {/* Capacity sub-label */}
      <text
        x={width / 2}
        y={height / 2 + 10}
        textAnchor="middle"
        dominantBaseline="central"
        className="pointer-events-none select-none fill-gray-400"
        style={{ fontSize: 10 }}
      >
        {capacityLabel}
      </text>
    </g>
  );
}
