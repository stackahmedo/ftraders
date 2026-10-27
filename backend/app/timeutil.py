from datetime import date, datetime, time, timedelta, timezone

from .config import BUSINESS_TZ

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(BUSINESS_TZ)
except Exception:  # tzdata missing (e.g. bare Windows): Bangladesh has no DST
    TZ = timezone(timedelta(hours=6))


def local_today() -> date:
    return datetime.now(TZ).date()


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Start/end of a local business day as naive UTC datetimes (how they are stored)."""
    start = datetime.combine(day, time.min, tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None)
    return start, start + timedelta(days=1)


def to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(TZ)
