"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useVenue } from "@/lib/venue";
import { formatTime, today, maxDate } from "@/lib/utils";
import type { AvailabilityResponse, AvailableSlot, Reservation } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type Step = "datetime" | "slot" | "guest" | "confirm";

export default function NewReservationPage() {
  const router = useRouter();
  const { current: venue } = useVenue();

  const [step, setStep] = useState<Step>("datetime");
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

  if (!venue) {
    return <p className="text-sm text-gray-400">No venue selected.</p>;
  }

  const fetchSlots = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.get<AvailabilityResponse>(
        `/venues/${venue.id}/availability?date=${date}&party_size=${partySize}`
      );
      setSlots(res.data.slots);
      if (res.data.slots.length === 0) {
        setError("No available slots for this date and party size.");
      } else {
        setStep("slot");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to check availability");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSlot = (slot: AvailableSlot) => {
    setSelectedSlot(slot);
    setStep("guest");
  };

  const handleSubmit = async () => {
    if (!selectedSlot) return;
    setError("");
    setLoading(true);
    try {
      await api.post<Reservation>(`/venues/${venue.id}/reservations`, {
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
        source: "admin",
      });
      router.push("/dashboard/reservations");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create reservation");
    } finally {
      setLoading(false);
    }
  };

  // Group slots by access rule name (meal period)
  const slotsByRule: Record<string, AvailableSlot[]> = {};
  for (const slot of slots) {
    const key = slot.access_rule_name;
    if (!slotsByRule[key]) slotsByRule[key] = [];
    slotsByRule[key].push(slot);
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/dashboard/reservations")}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          &larr; Back
        </button>
        <h1 className="text-xl font-semibold text-gray-900">
          New Reservation
        </h1>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Step 1: Date + Party Size */}
      {step === "datetime" && (
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="font-medium text-gray-900">Date & Party Size</h2>
          <Input
            label="Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            min={today()}
            max={maxDate()}
          />
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">
              Party Size
            </label>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Party size">
              {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  role="radio"
                  aria-checked={partySize === n}
                  aria-label={`${n} guest${n !== 1 ? "s" : ""}`}
                  onClick={() => setPartySize(n)}
                  className={`h-10 w-10 rounded-lg text-sm font-medium transition-colors ${
                    partySize === n
                      ? "bg-gray-900 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <Button onClick={fetchSlots} disabled={loading} className="w-full">
            {loading ? "Checking..." : "Check Availability"}
          </Button>
        </div>
      )}

      {/* Step 2: Slot Selection */}
      {step === "slot" && (
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-gray-900">Select Time</h2>
            <button
              onClick={() => setStep("datetime")}
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              Change date
            </button>
          </div>
          {Object.entries(slotsByRule).map(([ruleName, ruleSlots]) => (
            <div key={ruleName} className="space-y-2">
              <h3 className="text-sm font-medium text-gray-500">{ruleName}</h3>
              <div className="flex flex-wrap gap-2">
                {ruleSlots.map((slot) => (
                  <button
                    key={`${slot.time}-${slot.access_rule_id}`}
                    onClick={() => handleSelectSlot(slot)}
                    className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-900 hover:text-white transition-colors"
                  >
                    {formatTime(slot.time)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Step 3: Guest Info */}
      {step === "guest" && selectedSlot && (
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-gray-900">Guest Information</h2>
            <button
              onClick={() => setStep("slot")}
              className="text-sm text-gray-400 hover:text-gray-600"
            >
              Change time
            </button>
          </div>
          <p className="text-sm text-gray-500">
            {formatTime(selectedSlot.time)} &middot; {partySize} guest
            {partySize !== 1 ? "s" : ""} &middot;{" "}
            {selectedSlot.access_rule_name}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="First Name"
              value={guest.first_name}
              onChange={(e) =>
                setGuest((g) => ({ ...g, first_name: e.target.value }))
              }
              required
            />
            <Input
              label="Last Name"
              value={guest.last_name}
              onChange={(e) =>
                setGuest((g) => ({ ...g, last_name: e.target.value }))
              }
              required
            />
          </div>
          <Input
            label="Email"
            type="email"
            value={guest.email}
            onChange={(e) =>
              setGuest((g) => ({ ...g, email: e.target.value }))
            }
          />
          <Input
            label="Phone"
            type="tel"
            value={guest.phone}
            onChange={(e) =>
              setGuest((g) => ({ ...g, phone: e.target.value }))
            }
          />
          <Input
            label="Special Requests"
            value={specialRequests}
            onChange={(e) => setSpecialRequests(e.target.value)}
            placeholder="Allergies, celebrations, seating preferences..."
          />
          <Button
            onClick={() => setStep("confirm")}
            className="w-full"
            disabled={!guest.first_name || !guest.last_name}
          >
            Review Booking
          </Button>
        </div>
      )}

      {/* Step 4: Confirmation */}
      {step === "confirm" && selectedSlot && (
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="font-medium text-gray-900">Confirm Reservation</h2>
          <div className="rounded-lg bg-gray-50 p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Guest</span>
              <span className="font-medium">
                {guest.first_name} {guest.last_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Date</span>
              <span className="font-medium">{date}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Time</span>
              <span className="font-medium">
                {formatTime(selectedSlot.time)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Party Size</span>
              <span className="font-medium">{partySize}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Period</span>
              <span className="font-medium">
                {selectedSlot.access_rule_name}
              </span>
            </div>
            {specialRequests && (
              <div className="flex justify-between">
                <span className="text-gray-500">Requests</span>
                <span className="font-medium">{specialRequests}</span>
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setStep("guest")}
              className="flex-1"
            >
              Back
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={loading}
              className="flex-1"
            >
              {loading ? "Creating..." : "Create Reservation"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
