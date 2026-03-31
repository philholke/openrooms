/**
 * Format a time string (HH:MM:SS or HH:MM) to 12-hour display.
 */
export function formatTime(time: string): string {
  const [h, m] = time.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${period}`;
}

/**
 * Format a date string (YYYY-MM-DD) for display.
 */
export function formatDate(date: string): string {
  const d = new Date(date + "T00:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a datetime string for display.
 */
export function formatDateTime(datetime: string): string {
  const d = new Date(datetime);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Get today's date as YYYY-MM-DD in the user's local timezone.
 */
export function today(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Calculate elapsed minutes from a datetime string.
 */
export function minutesElapsed(from: string): number {
  return Math.floor((Date.now() - new Date(from).getTime()) / 60_000);
}

/**
 * Combine CSS class names, filtering out falsy values.
 */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
