// ─── API Envelope ────────────────────────────────────────────────────────

export interface Meta {
  page: number;
  per_page: number;
  total: number;
}

export interface ErrorDetail {
  field: string | null;
  message: string;
  code: string | null;
}

export interface Envelope<T> {
  data: T;
  meta: Meta | null;
  errors: ErrorDetail[] | null;
}

// ─── Auth ────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ─── Organization ────────────────────────────────────────────────────────

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Venue ───────────────────────────────────────────────────────────────

export interface Venue {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  address: string | null;
  timezone: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── User ────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: "owner" | "admin" | "manager" | "staff";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Guest ───────────────────────────────────────────────────────────────

export interface Guest {
  id: string;
  org_id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  birthday: string | null;
  anniversary: string | null;
  dietary_restrictions: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Access Rule ─────────────────────────────────────────────────────────

export interface AccessRule {
  id: string;
  venue_id: string;
  name: string;
  days_of_week: number[];
  start_date: string | null;
  end_date: string | null;
  start_time: string;
  end_time: string;
  slot_interval_minutes: number;
  min_party_size: number;
  max_party_size: number;
  max_covers_per_slot: number | null;
  advance_booking_days: number;
  cutoff_minutes: number;
  require_deposit: boolean;
  deposit_amount_cents: number | null;
  cancellation_policy_hours: number | null;
  cancellation_fee_cents: number | null;
  seating_areas: string[] | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Availability ────────────────────────────────────────────────────────

export interface AvailableSlot {
  time: string;
  access_rule_id: string;
  access_rule_name: string;
}

export interface AvailabilityResponse {
  venue_id: string;
  date: string;
  party_size: number;
  slots: AvailableSlot[];
}

// ─── Reservation ─────────────────────────────────────────────────────────

export type ReservationStatus =
  | "pending"
  | "confirmed"
  | "arrived"
  | "partially_arrived"
  | "seated"
  | "completed"
  | "no_show"
  | "cancelled";

export interface Reservation {
  id: string;
  venue_id: string;
  guest_id: string;
  table_id: string | null;
  access_rule_id: string | null;
  party_size: number;
  date: string;
  time: string;
  status: ReservationStatus;
  source: string | null;
  notes: string | null;
  special_requests: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  guest: Guest | null;
  table_label: string | null;
  access_rule_name: string | null;
}

// ─── Waitlist ────────────────────────────────────────────────────────────

export type WaitlistStatus =
  | "waiting"
  | "notified"
  | "seated"
  | "cancelled"
  | "no_show";

export interface WaitlistEntry {
  id: string;
  venue_id: string;
  guest_id: string;
  party_size: number;
  estimated_wait_minutes: number | null;
  status: WaitlistStatus;
  quoted_wait_minutes: number | null;
  check_in_time: string;
  seated_time: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  guest: Guest | null;
}

// ─── Table ───────────────────────────────────────────────────────────────

export interface Table {
  id: string;
  floor_plan_id: string;
  label: string;
  min_capacity: number;
  max_capacity: number;
  section: string | null;
  is_active: boolean;
}
