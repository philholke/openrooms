"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { Venue } from "./types";
import React from "react";

interface VenueState {
  venues: Venue[];
  current: Venue | null;
  setCurrent: (venue: Venue) => void;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const VenueContext = createContext<VenueState | null>(null);

export function VenueProvider({ children }: { children: ReactNode }) {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [current, setCurrentState] = useState<Venue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVenues = useCallback(async () => {
    setError(null);
    try {
      const res = await api.get<Venue[]>("/venues");
      const venueList = res.data;
      setVenues(venueList);

      // Restore last-selected venue or pick the first one
      const savedId = localStorage.getItem("selected_venue_id");
      const saved = venueList.find((v) => v.id === savedId);
      if (saved) {
        setCurrentState(saved);
      } else if (venueList.length > 0) {
        setCurrentState(venueList[0]);
        localStorage.setItem("selected_venue_id", venueList[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load venues");
      setVenues([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVenues();
  }, [fetchVenues]);

  const setCurrent = (venue: Venue) => {
    setCurrentState(venue);
    localStorage.setItem("selected_venue_id", venue.id);
  };

  return React.createElement(
    VenueContext.Provider,
    { value: { venues, current, setCurrent, loading, error, refresh: fetchVenues } },
    children
  );
}

export function useVenue(): VenueState {
  const ctx = useContext(VenueContext);
  if (!ctx) throw new Error("useVenue must be used within VenueProvider");
  return ctx;
}
