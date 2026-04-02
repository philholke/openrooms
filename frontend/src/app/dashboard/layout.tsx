"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { VenueProvider, useVenue } from "@/lib/venue";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const NAV_ITEMS = [
  { href: "/dashboard/reservations", label: "Reservations" },
  { href: "/dashboard/waitlist", label: "Waitlist" },
  { href: "/dashboard/guests", label: "Guests" },
  { href: "/dashboard/tags", label: "Tags" },
  { href: "/dashboard/floor-plans", label: "Floor Plans" },
  { href: "/dashboard/seating", label: "Seating" },
  { href: "/dashboard/pacing", label: "Pacing" },
  { href: "/dashboard/surveys", label: "Surveys" },
  { href: "/dashboard/analytics", label: "Analytics" },
  { href: "/dashboard/reports/pre-shift", label: "Pre-Shift" },
  { href: "/dashboard/settings", label: "Settings" },
];

function VenueSelector() {
  const { venues, current, setCurrent } = useVenue();

  if (venues.length <= 1) return null;

  return (
    <select
      value={current?.id || ""}
      onChange={(e) => {
        const v = venues.find((v) => v.id === e.target.value);
        if (v) setCurrent(v);
      }}
      className="w-full rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm"
    >
      {venues.map((v) => (
        <option key={v.id} value={v.id}>
          {v.name}
        </option>
      ))}
    </select>
  );
}

function Sidebar() {
  const pathname = usePathname();
  const { current } = useVenue();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-full w-56 flex-col border-r border-gray-200 bg-white">
      <div className="p-4">
        <Link href="/dashboard" className="text-lg font-bold text-gray-900">
          OpenRooms
        </Link>
      </div>

      <div className="px-3 pb-3">
        <VenueSelector />
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-gray-100 text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {current && (
        <div className="border-t border-gray-200 p-4">
          <p className="truncate text-xs text-gray-400">{current.name}</p>
          <p className="truncate text-xs text-gray-400">{current.timezone}</p>
        </div>
      )}
    </aside>
  );
}

function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="fixed left-56 right-0 top-0 z-30 flex h-14 items-center justify-end border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">{user?.full_name}</span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { loading: venueLoading } = useVenue();

  if (venueLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <TopBar />
      <main className="ml-56 pt-14">
        <div className="p-6">
          <ErrorBoundary>{children}</ErrorBoundary>
        </div>
      </main>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  // Show loading while auth state is resolving. Using `loading || !user`
  // ensures we never flash dashboard content before the user is confirmed.
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-400">Loading...</p>
      </div>
    );
  }

  if (!user) {
    // Auth check complete but no user — redirect is already in flight.
    // Return null to avoid a flash of the login page.
    return null;
  }

  return (
    <VenueProvider>
      <DashboardShell>{children}</DashboardShell>
    </VenueProvider>
  );
}
