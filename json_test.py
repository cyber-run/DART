import json

json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])

# Output: '["foo", {"bar": ["baz", null, 1.0, 2]}]'

json.loads('["foo", {"bar":["baz", null, 1.0, 2]}]')

# Output: ['foo', {'bar': ['baz', None, 1.0, 2]}]

print(json.dumps("\"foo\bar"))