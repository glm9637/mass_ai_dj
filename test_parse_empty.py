import sys
try:
    from homeassistant.util import dt as dt_util
    print(repr(dt_util.parse_datetime("")))
except ImportError:
    print("No homeassistant")
except Exception as e:
    print(repr(e))
