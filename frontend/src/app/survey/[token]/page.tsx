"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { publicFetch } from "@/lib/api";
import type { SurveyPublicInfo } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function PublicSurveyPage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<SurveyPublicInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    publicFetch<SurveyPublicInfo>(`/public/surveys/${token}`)
      .then(setInfo)
      .catch((err) => setError(err instanceof Error ? err.message : "Survey not found"))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const form = new FormData(e.currentTarget);
    const overallRaw = form.get("overall_rating") as string;
    if (!overallRaw || Number(overallRaw) < 1) {
      setError("Please select an overall rating.");
      setSubmitting(false);
      return;
    }
    const body: Record<string, unknown> = {
      overall_rating: Number(overallRaw),
    };
    for (const field of ["food_rating", "service_rating", "ambiance_rating", "drinks_rating"]) {
      const val = form.get(field) as string;
      if (val) body[field] = Number(val);
    }
    const comment = (form.get("comment") as string)?.trim();
    if (comment) body.comment = comment;

    try {
      const res = await fetch(`${API_BASE}/public/surveys/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as Record<string, string>).detail || "Submission failed");
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <PageShell>
        <p className="text-center text-sm text-gray-400">Loading...</p>
      </PageShell>
    );
  }

  if (error && !info) {
    return (
      <PageShell>
        <p className="text-center text-sm text-red-600">{error}</p>
        <p className="mt-2 text-center text-xs text-gray-400">
          This survey may have already been submitted or the link is invalid.
        </p>
      </PageShell>
    );
  }

  if (submitted) {
    return (
      <PageShell>
        <div className="text-center space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Thank you!</h2>
          <p className="text-sm text-gray-500">
            Your feedback for {info?.venue_name} has been submitted.
          </p>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <h2 className="text-lg font-semibold text-gray-900">
        How was your experience?
      </h2>
      <p className="text-sm text-gray-500">
        Hi {info?.guest_first_name}, thanks for visiting {info?.venue_name} on {info?.reservation_date}.
        We&apos;d love your feedback.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        {/* Overall rating (required) */}
        <RatingInput name="overall_rating" label="Overall *" required />
        <RatingInput name="food_rating" label="Food" />
        <RatingInput name="service_rating" label="Service" />
        <RatingInput name="ambiance_rating" label="Ambiance" />
        <RatingInput name="drinks_rating" label="Drinks" />

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Comments</label>
          <textarea
            name="comment"
            rows={3}
            maxLength={5000}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="Tell us more about your experience..."
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit Feedback"}
        </button>
      </form>
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-8 sm:py-16">
      <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-lg sm:p-8">
        {children}
      </div>
    </div>
  );
}

function RatingInput({
  name,
  label,
  required = false,
}: {
  name: string;
  label: string;
  required?: boolean;
}) {
  const [value, setValue] = useState<number | null>(null);

  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-700">{label}</label>
      <input type="hidden" name={name} value={value ?? ""} />
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setValue(star)}
            className="text-2xl transition-colors focus:outline-none"
            aria-label={`${star} star${star !== 1 ? "s" : ""}`}
          >
            <span className={star <= (value ?? 0) ? "text-yellow-400" : "text-gray-300"}>
              {"\u2605"}
            </span>
          </button>
        ))}
      </div>
      {required && !value && (
        <p className="mt-1 text-xs text-gray-400">Required</p>
      )}
    </div>
  );
}
