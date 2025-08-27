"""Centralized datetime utilities for consistent timezone handling"""
import pytz
from datetime import datetime

CHICAGO_TZ = pytz.timezone('America/Chicago')
UTC_TZ = pytz.UTC

def get_chicago_time():
    """Get current time in Chicago timezone"""
    return datetime.now(CHICAGO_TZ)

def make_chicago_aware(dt):
    """Convert naive datetime to Chicago timezone aware"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return CHICAGO_TZ.localize(dt)
    return dt.astimezone(CHICAGO_TZ)

def utc_to_chicago(dt):
    """Convert UTC datetime to Chicago timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    return dt.astimezone(CHICAGO_TZ)

def is_past_deadline(deadline):
    """Check if deadline has passed in Chicago time"""
    deadline_chicago = make_chicago_aware(deadline)
    current_chicago = get_chicago_time()
    return current_chicago > deadline_chicago

def format_chicago_time(dt, format_str='%B %d, %Y at %I:%M %p %Z'):
    """Format datetime in Chicago timezone"""
    if dt is None:
        return 'TBD'
    dt_chicago = make_chicago_aware(dt)
    return dt_chicago.strftime(format_str)