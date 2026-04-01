/**
 * Utility functions for the floor plan SVG editor.
 */

/** Snap a coordinate to the nearest grid increment. */
export function snapToGrid(value: number, gridSize: number = 10): number {
  return Math.round(value / gridSize) * gridSize;
}

/** Convert screen coordinates to SVG coordinates using the SVG CTM. */
export function screenToSvg(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): { x: number; y: number } {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: clientX, y: clientY };
  const svgPt = pt.matrixTransform(ctm.inverse());
  return { x: svgPt.x, y: svgPt.y };
}

/** Get default dimensions for a table shape based on capacity. */
export function getTableDimensions(
  shape: string,
  maxCapacity: number,
): { width: number; height: number } {
  const base = Math.max(60, 30 + maxCapacity * 8);
  switch (shape) {
    case "circle":
      return { width: base, height: base };
    case "square":
      return { width: base, height: base };
    case "rectangle":
    default:
      return { width: base * 1.4, height: base };
  }
}

/** Default position for a new table (center of the default viewport). */
export const DEFAULT_TABLE_POSITION = { x: 400, y: 300 };

/** Default canvas dimensions. */
export const CANVAS_WIDTH = 1200;
export const CANVAS_HEIGHT = 800;
