import json
import requests

PLUGINS_URL = 'https://api.napari-hub.org/plugins'
all_plugins = sorted(list(json.loads(requests.get(PLUGINS_URL).text.strip()).keys()))

with open('plugins.json', 'w') as f:
    json.dump(all_plugins, f)
