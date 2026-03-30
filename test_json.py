import datetime
from homeassistant.helpers.json import JSONEncoder
import json

d = datetime.datetime.now()
print(json.dumps({"date": d}, cls=JSONEncoder))
