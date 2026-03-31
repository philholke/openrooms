"use client";

import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function BookingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-8 sm:py-16">
          <div className="w-full max-w-md space-y-6 rounded-2xl bg-white p-6 shadow-lg sm:p-8 text-center">
            <h2 className="text-lg font-semibold text-gray-900">
              Something went wrong
            </h2>
            <p className="text-sm text-gray-500">
              We could not load the booking widget. Please try refreshing the
              page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              Refresh
            </button>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
