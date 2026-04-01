"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { today, formatTime } from "@/lib/utils";
import type { PreShiftReport } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function PreShiftReportPage() {
  const { current: venue } = useVenue();
  const [date, setDate] = useState(today());
  const [report, setReport] = useState<PreShiftReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!venue) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PreShiftReport>(
        `/venues/${venue.id}/pre-shift-report?date=${date}`,
      );
      setReport(res.data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [venue, date]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected</p>;
  }

  return (
    <div>
      {/* Controls — hidden when printing */}
      <div className="mb-6 flex items-center justify-between print:hidden">
        <h1 className="text-xl font-semibold text-gray-900">Pre-Shift Report</h1>
        <div className="flex items-center gap-3">
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40"
          />
          <Button variant="secondary" size="sm" onClick={fetchReport}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => window.print()}>
            Print
          </Button>
        </div>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600 print:hidden">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : report ? (
        <div className="space-y-6 print:space-y-4">
          {/* Print header */}
          <div className="hidden print:block">
            <h1 className="text-xl font-bold">{report.venue_name} — Pre-Shift Report</h1>
            <p className="text-sm text-gray-600">{report.date}</p>
          </div>

          {/* Summary stats */}
          <div className="flex gap-6 rounded-lg border border-gray-200 bg-white p-4 text-sm print:border print:p-3">
            <div>
              <p className="text-gray-500">Total Covers</p>
              <p className="text-2xl font-bold text-gray-900">{report.total_covers}</p>
            </div>
            <div>
              <p className="text-gray-500">Reservations</p>
              <p className="text-2xl font-bold text-gray-900">{report.total_reservations}</p>
            </div>
            <div>
              <p className="text-gray-500">Sections</p>
              <p className="text-2xl font-bold text-gray-900">{report.sections.length}</p>
            </div>
          </div>

          {/* Section summaries */}
          {report.sections.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-medium text-gray-600">Section Overview</h2>
              <div className="overflow-hidden rounded-lg border border-gray-200 print:border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 print:bg-gray-100">
                    <tr>
                      <th className="px-4 py-2 font-medium text-gray-600">Section</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Server</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Covers</th>
                      <th className="px-4 py-2 font-medium text-gray-600">Tables</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {report.sections.map((s) => (
                      <tr key={s.section}>
                        <td className="px-4 py-2 font-medium">{s.section}</td>
                        <td className="px-4 py-2 text-gray-600">{s.server_name || "—"}</td>
                        <td className="px-4 py-2">{s.covers}</td>
                        <td className="px-4 py-2">{s.table_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Reservation entries */}
          <div>
            <h2 className="mb-2 text-sm font-medium text-gray-600">Reservations</h2>
            {report.entries.length === 0 ? (
              <p className="text-sm text-gray-400">No reservations for this date.</p>
            ) : (
              <div className="overflow-hidden rounded-lg border border-gray-200 print:border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 print:bg-gray-100">
                    <tr>
                      <th className="px-3 py-2 font-medium text-gray-600">Time</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Guest</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Party</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Table</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Section</th>
                      <th className="px-3 py-2 font-medium text-gray-600">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {report.entries.map((entry, i) => (
                      <tr key={i} className="hover:bg-gray-50 print:hover:bg-transparent">
                        <td className="whitespace-nowrap px-3 py-2 font-medium">
                          {formatTime(entry.time)}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span>{entry.guest_name || "Walk-in"}</span>
                            {entry.visit_count > 0 && (
                              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                                {entry.visit_count} visits
                              </span>
                            )}
                          </div>
                          {entry.tags.length > 0 && (
                            <div className="mt-0.5 flex flex-wrap gap-1">
                              {entry.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="rounded bg-indigo-50 px-1.5 py-0.5 text-xs text-indigo-600"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2">{entry.party_size}</td>
                        <td className="px-3 py-2 text-gray-600">
                          {entry.table_label || "—"}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {entry.section || "—"}
                        </td>
                        <td className="max-w-xs px-3 py-2 text-gray-500">
                          {[
                            entry.dietary_restrictions &&
                              `Diet: ${entry.dietary_restrictions}`,
                            entry.special_requests,
                            entry.notes,
                          ]
                            .filter(Boolean)
                            .join(" | ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Print-specific styles */}
      <style jsx global>{`
        @media print {
          body > *:not(main),
          aside,
          header,
          nav {
            display: none !important;
          }
          main {
            margin-left: 0 !important;
            padding-top: 0 !important;
          }
          .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
