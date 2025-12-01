"""
Timezone utilities for PharmaBot
All timestamps use Asia/Dhaka timezone
Database stores naive UTC timestamps, but all operations use Asia/Dhaka timezone
"""
from datetime import datetime, timedelta
import pytz

# Define Asia/Dhaka timezone
DHAKA_TZ = pytz.timezone('Asia/Dhaka')


def now():
    """Get current datetime in Asia/Dhaka timezone as naive datetime for database compatibility"""
    # Get current time in Asia/Dhaka
    dhaka_time = datetime.now(DHAKA_TZ)
    # Return as naive datetime (remove timezone info for database storage)
    return dhaka_time.replace(tzinfo=None)


def today_start():
    """Get start of today (00:00:00) in Asia/Dhaka timezone"""
    current = now()
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def today_end():
    """Get end of today (23:59:59) in Asia/Dhaka timezone"""
    current = now()
    return current.replace(hour=23, minute=59, second=59, microsecond=999999)


def to_dhaka_aware(dt):
    """Convert a naive datetime to timezone-aware Asia/Dhaka datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is already in Dhaka time
        return DHAKA_TZ.localize(dt)
    return dt.astimezone(DHAKA_TZ)


def to_dhaka(dt):
    """Convert any datetime to Asia/Dhaka timezone and return as naive"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Already naive, assume it's in Dhaka time
        return dt
    # Convert to Dhaka and make naive
    return dt.astimezone(DHAKA_TZ).replace(tzinfo=None)
