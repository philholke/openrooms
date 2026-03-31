"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatTime, formatDate } from "@/lib/utils";
import type { Reservation, ReservationStatus } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";

// Allowed next statuses per current status (mirrors backend status machine)
const NEXT_ACTIONS: Record<
  string,
  { label: string; status: ReservationStatus; variant: "primary" | "secondary" | "danger" }[]
> = {
  pending: [
    { label: "Confirm", status: "confirmed", variant: "primary" },
    { label: "Cancel", status: "cancelled", variant: "danger" },
  ],
  confirmed: [
    { label: "Mark Arrived", status: "arrived", variant: "primary" },
    { label: "No Show", status: "no_show", variant: "danger" },
    { label: "Cancel", status: "cancelled", variant: "danger" },
  ],
  arrived: [
    { label: "Seat", status: "seated", variant: "primary" },
    { label: "No Show", status: "no_show", variant: "danger" },
  ],
  partially_arrived: [
    { label: "Seat", status: "seated", variant: "primary" },
    { label: "No Show", status: "no_show", variant: "danger" },
  ],
  seated: [
    { label: "Complete", status: "completed", variant: "primary" },
  ],
};

interface Props {
  reservation: Reservation;
  open: boolean;
  onClose: () => void;
  onUpdated: () => void;
}

export function ReservationDetail({
  reservation,
  open,
  onClose,
  onUpdated,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleStatusChange = async (newStatus: ReservationStatus) => {
    setError("");
    setLoading(true);
    try {
      if (newStatus === "cancelled") {
        await api.post(`/reservations/${reservation.id}/cancel`, {});
      } else {
        await api.patch(`/reservations/${reservation.id}/status`, {
          status: newStatus,
        });
      }
      onUpdated();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update status");
    } finally {
      setLoading(false);
    }
  };

  const actions = NEXT_ACTIONS[reservation.status] || [];
  const guest = reservation.guest;

  return (
    <Modal open={open} onClose={onClose} title="Reservation Details" className="max-w-md">
      <div className="space-y-4">
        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {/* Status */}
        <div className="flex items-center justify-between">
          <StatusBadge status={reservation.status} />
          <span className="text-sm text-gray-400">
            {reservation.source || "—"}
          </span>
        </div>

        {/* Guest info */}
        <div className="rounded-lg bg-gray-50 p-3 space-y-1">
          <p className="font-medium text-gray-900">
            {guest ? `${guest.first_name} ${guest.last_name}` : "Unknown Guest"}
          </p>
          {guest?.email && (
            <p className="text-sm text-gray-500">{guest.email}</p>
          )}
          {guest?.phone && (
            <p className="text-sm text-gray-500">{guest.phone}</p>
          )}
          {guest?.dietary_restrictions && (
            <p className="text-sm text-amber-700">
              Dietary: {guest.dietary_restrictions}
            </p>
          )}
        </div>

        {/* Booking details */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">Date</span>
            <p className="font-medium">{formatDate(reservation.date)}</p>
          </div>
          <div>
            <span className="text-gray-400">Time</span>
            <p className="font-medium">{formatTime(reservation.time)}</p>
          </div>
          <div>
            <span className="text-gray-400">Party Size</span>
            <p className="font-medium">{reservation.party_size}</p>
          </div>
          <div>
            <span className="text-gray-400">Table</span>
            <p className="font-medium">{reservation.table_label || "Unassigned"}</p>
          </div>
        </div>

        {/* Access rule */}
        {reservation.access_rule_name && (
          <div className="text-sm">
            <span className="text-gray-400">Access Rule</span>
            <p className="font-medium">{reservation.access_rule_name}</p>
          </div>
        )}

        {/* Notes */}
        {reservation.special_requests && (
          <div className="text-sm">
            <span className="text-gray-400">Special Requests</span>
            <p>{reservation.special_requests}</p>
          </div>
        )}
        {reservation.notes && (
          <div className="text-sm">
            <span className="text-gray-400">Notes</span>
            <p>{reservation.notes}</p>
          </div>
        )}

        {/* Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
            {actions.map((action) => (
              <Button
                key={action.status}
                variant={action.variant}
                size="sm"
                onClick={() => handleStatusChange(action.status)}
                disabled={loading}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
