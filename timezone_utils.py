"""
Timezone utilities for the survivor pool
Handles all timezone conversions and datetime operations
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os

# Get the pool's timezone from environment or default to Chicago
POOL_TZ_NAME = os.getenv('POOL_TIMEZONE', 'America/Chicago')
POOL_TZ = ZoneInfo(POOL_TZ_NAME)
UTC_TZ = timezone.utc

def get_current_time():
    """Get current time in the pool's timezone (aware)"""
    return datetime.now(POOL_TZ)

def get_utc_time():
    """Get current UTC time (aware)"""
    return datetime.now(UTC_TZ)

def make_aware(dt, tz=POOL_TZ):
    """Convert naive datetime to aware in specified timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetimes are in pool timezone
        return dt.replace(tzinfo=tz)
    return dt

def to_utc(dt):
    """Convert any datetime to UTC"""
    if dt is None:
        return None
    dt_aware = make_aware(dt)
    return dt_aware.astimezone(UTC_TZ)

def to_pool_time(dt):
    """Convert any datetime to pool timezone"""
    if dt is None:
        return None
    dt_aware = make_aware(dt, UTC_TZ)  # If naive, assume UTC (from database)
    return dt_aware.astimezone(POOL_TZ)

def deadline_has_passed(deadline):
    """Check if a deadline has passed"""
    deadline_aware = make_aware(deadline)
    current = get_current_time()
    return current > deadline_aware

def format_deadline(deadline):
    """Format deadline for display in Chicago timezone"""
    if deadline is None:
        return 'TBD'

    chicago_tz = ZoneInfo('America/Chicago')

    # If deadline has timezone info, convert to Chicago
    if deadline.tzinfo is not None:
        deadline_chicago = deadline.astimezone(chicago_tz)
    else:
        # If naive, assume it's already in Chicago time
        deadline_chicago = deadline.replace(tzinfo=chicago_tz)

    # Format with CDT/CST shown
    return deadline_chicago.strftime('%B %d, %Y at %I:%M %p %Z')

def parse_form_datetime(datetime_str):
    """Parse datetime from form input and make it timezone-aware in pool timezone"""
    naive_dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
    return naive_dt.replace(tzinfo=POOL_TZ)

def safe_is_after(dt1, dt2):
    """Safely compare two datetimes, handling mixed naive/aware.
    Returns True if dt1 is after dt2."""
    if dt1 is None or dt2 is None:
        return False
    # Normalize both to aware in pool timezone
    dt1_aware = make_aware(dt1)
    dt2_aware = make_aware(dt2)
    return dt1_aware > dt2_aware
