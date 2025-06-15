# utils/boosts.py

from datetime import datetime
import pytz

def is_weekend_boost_active():
    now = datetime.now(pytz.utc)
    if now.weekday() in [4, 5, 6]:  # Friday, Saturday, Sunday
        if now.weekday() == 4 and now.hour < 6:
            return False  # Not active yet on Friday
        return True
    return False
