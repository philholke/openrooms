"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { publicFetch } from "@/lib/api";
import { formatTime, today, cn } from "@/lib/utils";
import type {
  AvailabilityResponse,
  AvailableSlot,
  Reservation,
  Venue,
} from "@/lib/types";

// ─── Types ──────────────────────────────────────────────────────────────

type Step = "date" | "time" | "guest" | "confirm" | "success";

// ─── Widget Component ───────────────────────────────────────────────────

export default function BookingWidget() {
  const params = useParams();
  const searchParams = useSearchParams();
  const venueId = params.venueId as string;

  // Theming from URL params — validate as hex to prevent CSS injection
  const rawColor = searchParams.get("primaryColor") || "111827";
  const primaryColor = /^[0-9A-Fa-f]{3,8}$/.test(rawColor) ? rawColor : "111827";
  const primaryStyle = { backgroundColor: `#${primaryColor}` };

  // State
  const [venue, setVenue] = useState<Venue | null>(null);
  const [venueError, setVenueError] = useState("");
  const [step, setStep] = useState<Step>("date");
  const [date, setDate] = useState(today());
  const [partySize, setPartySize] = useState(2);
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [guest, setGuest] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
  });
  const [specialRequests, setSpecialRequests] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState<Reservation | null>(null);

  const [venueLoading, setVenueLoading] = useState(true);

  // Load venue info
  useEffect(() => {
    setVenueLoading(true);
    publicFetch<Venue>(`/venues/${venueId}`)
      .then(setVenue)
      .catch(() => setVenueError("Venue not found"))
      .finally(() => setVenueLoading(false));
  }, [venueId]);

  // Fetch availability
  const fetchSlots = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const data = await publicFetch<AvailabilityResponse>(
        `/venues/${venueId}/availability?date=${date}&party_size=${partySize}`
      );
      setSlots(data.slots);
      if (data.slots.length === 0) {
        setError("No available times for this date and party size.");
      } else {
        setStep("time");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check availability");
    } finally {
      setLoading(false);
    }
  }, [venueId, date, partySize]);

  // Client-side validation
  const validateGuest = (): string | null => {
    if (!guest.first_name.trim() || !guest.last_name.trim()) return "Name is required.";
    if (!guest.email.trim()) return "Email is required.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(guest.email)) return "Please enter a valid email address.";
    if (guest.phone && !/^[+\d\s()-]{7,20}$/.test(guest.phone)) return "Please enter a valid phone number.";
    return null;
  };

  // Submit reservation
  const handleBook = async () => {
    if (!selectedSlot) return;
    const validationError = validateGuest();
    if (validationError) { setError(validationError); return; }
    setError("");
    setLoading(true);
    try {
      const res = await publicFetch<Reservation>(
        `/venues/${venueId}/reservations`,
        {
          method: "POST",
          body: JSON.stringify({
            date,
            time: selectedSlot.time,
            party_size: partySize,
            access_rule_id: selectedSlot.access_rule_id,
            guest: {
              first_name: guest.first_name,
              last_name: guest.last_name,
              email: guest.email || null,
              phone: guest.phone || null,
            },
            special_requests: specialRequests || null,
            source: "widget",
          }),
        }
      );
      setConfirmation(res);
      setStep("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  };

  // Group slots by meal period
  const slotsByRule: Record<string, AvailableSlot[]> = {};
  for (const slot of slots) {
    if (!slotsByRule[slot.access_rule_name]) slotsByRule[slot.access_rule_name] = [];
    slotsByRule[slot.access_rule_name].push(slot);
  }

  // ── Loading / error states ──
  if (venueLoading) {
    return (
      <WidgetShell>
        <p className="text-center text-gray-400 py-12">Loading...</p>
      </WidgetShell>
    );
  }

  if (venueError) {
    return (
      <WidgetShell>
        <p className="text-center text-gray-500 py-12">{venueError}</p>
      </WidgetShell>
    );
  }

  return (
    <WidgetShell>
      {/* Venue header */}
      {venue && (
        <div className="text-center pb-2">
          <h1 className="text-2xl font-bold text-gray-900">{venue.name}</h1>
          {venue.address && (
            <p className="text-sm text-gray-500 mt-1">{venue.address}</p>
          )}
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* ── Step 1: Date & Party Size ── */}
      {step === "date" && (
        <div className="space-y-5">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              min={today()}
              className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">
              Party Size
            </label>
            <div className="grid grid-cols-5 gap-2" role="radiogroup" aria-label="Party size">
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  role="radio"
                  aria-checked={partySize === n}
                  aria-label={`${n} guest${n !== 1 ? "s" : ""}`}
                  onClick={() => setPartySize(n)}
                  className={cn(
                    "rounded-lg py-2.5 text-sm font-medium transition-colors",
                    partySize === n
                      ? "text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                  style={partySize === n ? primaryStyle : undefined}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={fetchSlots}
            disabled={loading}
            className="w-full rounded-lg py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
            style={primaryStyle}
          >
            {loading ? "Checking availability..." : "Find a Table"}
          </button>
        </div>
      )}

      {/* ── Step 2: Time Slot Selection ── */}
      {step === "time" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}{" "}
              &middot; {partySize} guest{partySize !== 1 ? "s" : ""}
            </p>
            <button
              onClick={() => setStep("date")}
              className="text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              Change
            </button>
          </div>

          {Object.entries(slotsByRule).map(([ruleName, ruleSlots]) => (
            <div key={ruleName} className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                {ruleName}
              </h3>
              <div className="grid grid-cols-3 gap-2">
                {ruleSlots.map((slot) => (
                  <button
                    key={`${slot.time}-${slot.access_rule_id}`}
                    onClick={() => {
                      setSelectedSlot(slot);
                      setStep("guest");
                    }}
                    className="rounded-lg border border-gray-200 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:border-gray-400 hover:bg-gray-50"
                  >
                    {formatTime(slot.time)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Step 3: Guest Information ── */}
      {step === "guest" && selectedSlot && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {formatTime(selectedSlot.time)} &middot; {partySize} guest
              {partySize !== 1 ? "s" : ""}
            </p>
            <button
              onClick={() => setStep("time")}
              className="text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              Change time
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-gray-600">
                First Name *
              </label>
              <input
                value={guest.first_name}
                onChange={(e) =>
                  setGuest((g) => ({ ...g, first_name: e.target.value }))
                }
                required
                className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-gray-600">
                Last Name *
              </label>
              <input
                value={guest.last_name}
                onChange={(e) =>
                  setGuest((g) => ({ ...g, last_name: e.target.value }))
                }
                required
                className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">
              Email *
            </label>
            <input
              type="email"
              value={guest.email}
              onChange={(e) =>
                setGuest((g) => ({ ...g, email: e.target.value }))
              }
              required
              className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">
              Phone
            </label>
            <input
              type="tel"
              value={guest.phone}
              onChange={(e) =>
                setGuest((g) => ({ ...g, phone: e.target.value }))
              }
              className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">
              Special Requests
            </label>
            <textarea
              value={specialRequests}
              onChange={(e) => setSpecialRequests(e.target.value)}
              rows={2}
              placeholder="Allergies, celebrations, seating preferences..."
              className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 resize-none"
            />
          </div>

          <button
            onClick={() => {
              const err = validateGuest();
              if (err) { setError(err); return; }
              setError("");
              setStep("confirm");
            }}
            disabled={!guest.first_name || !guest.last_name || !guest.email}
            className="w-full rounded-lg py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
            style={primaryStyle}
          >
            Review Booking
          </button>
        </div>
      )}

      {/* ── Step 4: Confirmation ── */}
      {step === "confirm" && selectedSlot && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Confirm Your Reservation
          </h2>

          <div className="rounded-lg bg-gray-50 p-4 space-y-3 text-sm">
            <Row label="Restaurant" value={venue?.name || ""} />
            <Row
              label="Date"
              value={new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            />
            <Row label="Time" value={formatTime(selectedSlot.time)} />
            <Row
              label="Party Size"
              value={`${partySize} guest${partySize !== 1 ? "s" : ""}`}
            />
            <Row
              label="Name"
              value={`${guest.first_name} ${guest.last_name}`}
            />
            <Row label="Email" value={guest.email} />
            {guest.phone && <Row label="Phone" value={guest.phone} />}
            {specialRequests && (
              <Row label="Requests" value={specialRequests} />
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep("guest")}
              className="flex-1 rounded-lg border border-gray-300 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={handleBook}
              disabled={loading}
              className="flex-1 rounded-lg py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
              style={primaryStyle}
            >
              {loading ? "Booking..." : "Confirm Booking"}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 5: Success ── */}
      {step === "success" && confirmation && (
        <div className="text-center space-y-4 py-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <svg
              className="h-8 w-8 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">
            Reservation Confirmed!
          </h2>
          <div className="space-y-1 text-sm text-gray-600">
            <p>
              {new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </p>
            <p>
              {selectedSlot && formatTime(selectedSlot.time)} &middot; {partySize} guest
              {partySize !== 1 ? "s" : ""}
            </p>
            <p>{venue?.name}</p>
          </div>
          <p className="text-xs text-gray-400">
            A confirmation has been sent to {guest.email}
          </p>
          <button
            onClick={() => {
              setStep("date");
              setSelectedSlot(null);
              setGuest({ first_name: "", last_name: "", email: "", phone: "" });
              setSpecialRequests("");
              setConfirmation(null);
              setError("");
            }}
            className="text-sm font-medium text-gray-500 hover:text-gray-700"
          >
            Make another reservation
          </button>
        </div>
      )}
    </WidgetShell>
  );
}

// ─── Layout shell ───────────────────────────────────────────────────────

function WidgetShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-8 sm:py-16">
      <div className="w-full max-w-md space-y-6 rounded-2xl bg-white p-6 shadow-lg sm:p-8">
        {children}
      </div>
    </div>
  );
}

// ─── Small helpers ──────────────────────────────────────────────────────

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900 text-right">{value}</span>
    </div>
  );
}
