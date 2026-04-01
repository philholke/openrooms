"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ServerAssignment, User } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

interface ServerAssignmentPanelProps {
  venueId: string;
  date: string;
  sections: string[];
}

export function ServerAssignmentPanel({
  venueId,
  date,
  sections,
}: ServerAssignmentPanelProps) {
  const [assignments, setAssignments] = useState<ServerAssignment[]>([]);
  const [staff, setStaff] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get<ServerAssignment[]>(
        `/venues/${venueId}/server-assignments?date=${date}`,
      ),
      api.get<User[]>("/users?per_page=100"),
    ])
      .then(([aRes, uRes]) => {
        setAssignments(aRes.data);
        setStaff(uRes.data);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, [venueId, date]);

  const handleAssign = async (section: string, userId: string) => {
    setError("");
    try {
      const res = await api.post<ServerAssignment>(
        `/venues/${venueId}/server-assignments`,
        { date, section, user_id: userId },
      );
      setAssignments((prev) => {
        const filtered = prev.filter((a) => a.section !== section);
        return [...filtered, res.data];
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign");
    }
  };

  const handleRemove = async (assignmentId: string, section: string) => {
    try {
      await api.delete(`/server-assignments/${assignmentId}`);
      setAssignments((prev) => prev.filter((a) => a.id !== assignmentId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove");
    }
  };

  if (loading) {
    return (
      <div className="w-64 rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm text-gray-400">Loading...</p>
      </div>
    );
  }

  const staffOptions = [
    { value: "", label: "Unassigned" },
    ...staff.map((u) => ({ value: u.id, label: u.full_name })),
  ];

  const assignmentBySection = new Map(
    assignments.map((a) => [a.section, a]),
  );

  return (
    <div className="w-64 space-y-3 rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-medium text-gray-900">Server Assignments</h3>
      <p className="text-xs text-gray-400">{date}</p>

      {error && (
        <div role="alert" className="text-xs text-red-600">{error}</div>
      )}

      {sections.length === 0 ? (
        <p className="text-xs text-gray-400">
          No sections defined. Add sections to your tables.
        </p>
      ) : (
        <div className="space-y-3">
          {sections.map((section) => {
            const assignment = assignmentBySection.get(section);
            return (
              <div key={section}>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  {section}
                </label>
                <div className="flex items-center gap-1">
                  <Select
                    label=""
                    value={assignment?.user_id || ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val) {
                        handleAssign(section, val);
                      } else if (assignment) {
                        handleRemove(assignment.id, section);
                      }
                    }}
                    options={staffOptions}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
