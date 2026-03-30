import sys
try:
    from homeassistant.util import dt as dt_util
    print(repr(dt_util.parse_datetime(None)))
except ImportError:
    print("No homeassistant")
