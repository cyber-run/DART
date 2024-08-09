import json

settings = '''
{
    "profiles": [
        {
            "id": "default",
            "ports": {
                "dynamixel": "COM5",
                "theia": "COM17"
            },
            "tracker_camera": 0,
            "static_camera": 1,
            "exposure": 400,
            "gain": 10
        }
    ]
}
'''

data = json.loads(settings)

print(data['profiles'][0]['ports']['dynamixel'])
print(data['profiles'][0]['ports']['theia'])
print(data['profiles'][0]['tracker_camera'])
print(data['profiles'][0]['static_camera'])
print(data['profiles'][0]['exposure'])
print(data['profiles'][0]['gain'])
print(data)