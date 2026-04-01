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

// ─── Floor Plan ─────────────────────────────────────────────────────────

export interface FloorPlan {
  id: string;
  venue_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Table ───────────────────────────────────────────────────────────────

export interface Table {
  id: string;
  floor_plan_id: string;
  label: string;
  min_capacity: number;
  max_capacity: number;
  section: string | null;
  x_position: number | null;
  y_position: number | null;
  shape: string;
  held_until: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type TableStatus = "available" | "occupied" | "reserved" | "held";

export interface TableWithStatus extends Table {
  status: TableStatus;
  current_reservation_id: string | null;
  current_guest_name: string | null;
  current_party_size: number | null;
  next_reservation_time: string | null;
}

// ─── Server Assignment ──────────────────────────────────────────────────

export interface ServerAssignment {
  id: string;
  venue_id: string;
  date: string;
  section: string;
  user_id: string;
  user_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Pacing ─────────────────────────────────────────────────────────────

export interface PacingSlot {
  time: string;
  booked_covers: number;
  capacity: number;
}

// ─── Tag ────────────────────────────────────────────────────────────────

export interface Tag {
  id: string;
  org_id: string;
  name: string;
  color: string | null;
  is_auto: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutoTagConditions {
  visit_count_gte?: number | null;
  visit_count_lte?: number | null;
  last_visit_within_days?: number | null;
  last_visit_not_within_days?: number | null;
  total_spend_gte?: number | null;
  avg_rating_gte?: number | null;
  avg_rating_lte?: number | null;
  has_tag?: string | null;
  not_has_tag?: string | null;
  venue_id?: string | null;
}

export interface AutoTagRule {
  id: string;
  tag_id: string;
  org_id: string;
  conditions: AutoTagConditions;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BulkEvaluateResult {
  guests_evaluated: number;
  tags_applied: number;
  tags_removed: number;
}

// ─── Guest CRM ──────────────────────────────────────────────────────────

export interface GuestListItem {
  id: string;
  org_id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  total_visits: number;
  tag_names: string[];
  created_at: string;
}

export interface GuestVisit {
  id: string;
  venue_id: string;
  venue_name: string;
  reservation_id: string | null;
  visited_at: string;
  spend_amount: number | null;
  notes: string | null;
}

export interface Survey {
  id: string;
  venue_id: string;
  guest_id: string;
  reservation_id: string | null;
  overall_rating: number;
  food_rating: number | null;
  service_rating: number | null;
  ambiance_rating: number | null;
  drinks_rating: number | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface GuestDetail extends Guest {
  tags: Tag[];
  visits: GuestVisit[];
  surveys: Survey[];
  total_visits: number;
  last_visit_date: string | null;
  avg_overall_rating: number | null;
}

// ─── Survey Stats ───────────────────────────────────────────────────────

export interface RatingDistribution {
  rating: number;
  count: number;
}

export interface SurveyStats {
  total_responses: number;
  avg_overall: number | null;
  avg_food: number | null;
  avg_service: number | null;
  avg_ambiance: number | null;
  avg_drinks: number | null;
  distribution: RatingDistribution[];
}

export interface SurveyPublicInfo {
  venue_name: string;
  guest_first_name: string;
  reservation_date: string;
}

// ─── Pre-Shift Report ───────────────────────────────────────────────────

export interface SectionSummary {
  section: string;
  server_name: string | null;
  covers: number;
  table_count: number;
}

export interface PreShiftReportEntry {
  time: string;
  guest_name: string;
  party_size: number;
  table_label: string | null;
  section: string | null;
  status: string;
  special_requests: string | null;
  notes: string | null;
  dietary_restrictions: string | null;
  tags: string[];
  visit_count: number;
}

export interface PreShiftReport {
  date: string;
  venue_name: string;
  total_covers: number;
  total_reservations: number;
  sections: SectionSummary[];
  entries: PreShiftReportEntry[];
}
