"""
Timezone utilities for the survivor pool
Handles all timezone conversions and datetime operations
"""

from datetime import datetime, timezone
import pytz
import os

# Get the pool's timezone from environment or default to Chicago
POOL_TZ_NAME = os.getenv('POOL_TIMEZONE', 'America/Chicago')
POOL_TZ = pytz.timezone(POOL_TZ_NAME)
UTC_TZ = pytz.UTC

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
        return tz.localize(dt)
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
    """Format deadline for display in pool timezone"""
    deadline_aware = to_pool_time(deadline)
    return deadline_aware.strftime('%B %d, %Y at %I:%M %p %Z')

def parse_form_datetime(datetime_str):
    """Parse datetime from form input and make it timezone-aware in pool timezone"""
    naive_dt = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
    return POOL_TZ.localize(naive_dt)