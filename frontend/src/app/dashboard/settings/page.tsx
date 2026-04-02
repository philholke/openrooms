"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useVenue } from "@/lib/venue";

interface NotificationPref {
  id: string;
  venue_id: string;
  notification_type: string;
  enabled: boolean;
}

const NOTIFICATION_LABELS: Record<string, { label: string; description: string; category: string }> = {
  reservation_confirmed: {
    label: "Reservation Confirmation",
    description: "Email sent to guests when a reservation is confirmed",
    category: "Guest Notifications",
  },
  reservation_reminder: {
    label: "Reservation Reminder",
    description: "Email sent to guests the day before their reservation",
    category: "Guest Notifications",
  },
  survey_invite: {
    label: "Survey Invite",
    description: "Email sent to guests after their visit to collect feedback",
    category: "Guest Notifications",
  },
  cancellation_ack: {
    label: "Cancellation Acknowledgement",
    description: "Email sent to guests when their reservation is cancelled",
    category: "Guest Notifications",
  },
  welcome: {
    label: "Welcome Email",
    description: "Email sent to first-time guests after their initial reservation",
    category: "Guest Notifications",
  },
  pre_shift_report: {
    label: "Pre-Shift Report",
    description: "Daily email sent to managers with the upcoming shift report",
    category: "Staff Notifications",
  },
};

export default function SettingsPage() {
  const { current: venue } = useVenue();
  const [prefs, setPrefs] = useState<NotificationPref[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!venue) return;
    setLoading(true);
    api
      .get<NotificationPref[]>(
        `/venues/${venue.id}/notification-preferences`
      )
      .then((res) => setPrefs(res.data))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load preferences")
      )
      .finally(() => setLoading(false));
  }, [venue]);

  const handleToggle = async (notificationType: string, enabled: boolean) => {
    if (!venue) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await api.patch<NotificationPref[]>(
        `/venues/${venue.id}/notification-preferences`,
        [{ notification_type: notificationType, enabled }]
      );
      setPrefs(updated.data);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSaving(false);
    }
  };

  if (!venue) {
    return <div className="p-6 text-zinc-500">Select a venue to manage settings.</div>;
  }

  const categories = ["Guest Notifications", "Staff Notifications"];

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-zinc-900 mb-1">
        Notification Settings
      </h1>
      <p className="text-sm text-zinc-500 mb-6">
        Control which email notifications are sent for {venue.name}.
      </p>

      {error && (
        <div role="alert" className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-md mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 text-green-700 text-sm px-4 py-3 rounded-md mb-4">
          Settings saved
        </div>
      )}

      {loading ? (
        <p className="text-zinc-400 text-sm">Loading...</p>
      ) : (
        <div className="space-y-6">
          {categories.map((category) => {
            const items = prefs.filter(
              (p) => NOTIFICATION_LABELS[p.notification_type]?.category === category
            );
            if (items.length === 0) return null;
            return (
              <div key={category}>
                <h2 className="text-sm font-medium text-zinc-700 mb-3">
                  {category}
                </h2>
                <div className="bg-white rounded-lg border border-zinc-200 divide-y divide-zinc-100">
                  {items.map((pref) => {
                    const meta = NOTIFICATION_LABELS[pref.notification_type];
                    return (
                      <div
                        key={pref.notification_type}
                        className="flex items-center justify-between p-4"
                      >
                        <div>
                          <p className="text-sm font-medium text-zinc-900">
                            {meta?.label || pref.notification_type}
                          </p>
                          <p className="text-xs text-zinc-500 mt-0.5">
                            {meta?.description}
                          </p>
                        </div>
                        <button
                          onClick={() =>
                            handleToggle(pref.notification_type, !pref.enabled)
                          }
                          disabled={saving}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            pref.enabled ? "bg-zinc-900" : "bg-zinc-200"
                          }`}
                          role="switch"
                          aria-checked={pref.enabled}
                        >
                          <span
                            className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                              pref.enabled ? "translate-x-6" : "translate-x-1"
                            }`}
                          />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
