import sys
import json

with open(sys.argv[2]) as data:
   d = {}
   d[sys.argv[1]] = data.read()
   print(json.dumps(d))
