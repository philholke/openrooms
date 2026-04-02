"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { publicFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ReservationInfo {
  venue_name: string;
  venue_address: string | null;
  guest_first_name: string | null;
  reservation_date: string;
  reservation_time: string;
  party_size: number;
  status: string;
  special_requests: string | null;
  cancellation_policy_hours: number | null;
}

export default function CancelReservationPage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<ReservationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelled, setCancelled] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    publicFetch<ReservationInfo>(`/public/reservations/${token}`)
      .then((data) => {
        setInfo(data);
        if (data.status === "cancelled") setCancelled(true);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Reservation not found")
      )
      .finally(() => setLoading(false));
  }, [token]);

  const handleCancel = async () => {
    setCancelling(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/public/reservations/${token}/cancel`,
        { method: "POST", headers: { "Content-Type": "application/json" } }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(
          (data as Record<string, string>).detail || "Cancellation failed"
        );
      }
      setCancelled(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancellation failed");
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <p className="text-zinc-500">Loading reservation...</p>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 text-center">
          <h1 className="text-xl font-semibold text-zinc-900 mb-2">
            Reservation Not Found
          </h1>
          <p className="text-zinc-500">
            This cancellation link may have expired or is no longer valid.
          </p>
        </div>
      </div>
    );
  }

  if (cancelled) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-zinc-900 mb-2">
            Reservation Cancelled
          </h1>
          <p className="text-zinc-500 mb-6">
            Your reservation at {info?.venue_name} has been cancelled.
          </p>
          <p className="text-sm text-zinc-400">
            We hope to see you again soon.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-sm overflow-hidden">
        {/* Header */}
        <div className="bg-zinc-900 px-6 py-5">
          <h1 className="text-lg font-semibold text-white">
            {info?.venue_name}
          </h1>
          {info?.venue_address && (
            <p className="text-zinc-400 text-sm mt-1">{info.venue_address}</p>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          <h2 className="text-lg font-semibold text-zinc-900 mb-4">
            Cancel Reservation
          </h2>

          {info?.guest_first_name && (
            <p className="text-zinc-600 mb-4">
              Hi {info.guest_first_name}, would you like to cancel this
              reservation?
            </p>
          )}

          {/* Details */}
          <div className="bg-zinc-50 rounded-md p-4 mb-6 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500">Date</span>
              <span className="text-zinc-900 font-medium">
                {info?.reservation_date}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500">Time</span>
              <span className="text-zinc-900 font-medium">
                {info?.reservation_time}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500">Party size</span>
              <span className="text-zinc-900 font-medium">
                {info?.party_size}{" "}
                {info?.party_size === 1 ? "guest" : "guests"}
              </span>
            </div>
            {info?.special_requests && (
              <div className="flex justify-between text-sm">
                <span className="text-zinc-500">Special requests</span>
                <span className="text-zinc-900 font-medium">
                  {info.special_requests}
                </span>
              </div>
            )}
          </div>

          {info?.cancellation_policy_hours && (
            <p className="text-xs text-zinc-500 mb-4">
              Cancellation policy: Free cancellation up to{" "}
              {info.cancellation_policy_hours} hours before the reservation.
            </p>
          )}

          {error && (
            <div
              role="alert"
              className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-md mb-4"
            >
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2.5 px-4 rounded-md text-sm disabled:opacity-50 transition-colors"
            >
              {cancelling ? "Cancelling..." : "Cancel Reservation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
