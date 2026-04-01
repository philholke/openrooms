import uuid
from datetime import date

from pydantic import BaseModel


class SectionSummary(BaseModel):
    section: str
    server_name: str | None = None
    covers: int
    table_count: int


class PreShiftReportEntry(BaseModel):
    time: str
    guest_name: str
    party_size: int
    table_label: str | None = None
    section: str | None = None
    status: str
    special_requests: str | None = None
    notes: str | None = None
    dietary_restrictions: str | None = None
    tags: list[str] = []
    visit_count: int = 0


class PreShiftReport(BaseModel):
    date: date
    venue_name: str
    total_covers: int
    total_reservations: int
    sections: list[SectionSummary]
    entries: list[PreShiftReportEntry]
