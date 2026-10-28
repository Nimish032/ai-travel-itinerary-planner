"""Tests for PDF export."""

from datetime import datetime, timezone

from core.demo_data import demo_itinerary
from core.models import SavedTrip, TripPreferences
from core.pdf_export import generate_pdf


def test_pdf_export_returns_pdf_bytes():
    now = datetime.now(timezone.utc)
    trip = SavedTrip(
        id="pdf-test", title="Paris test", created_at=now, updated_at=now,
        preferences=TripPreferences(destination="Paris", days=2),
        itinerary=demo_itinerary("Paris", 2),
    )
    data = generate_pdf(trip)
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
