import json
from pathlib import Path
import requests

# Trying to imagine Manufacturing value added (% of GDP) for Nigeria
URL = "https://api.worldbank.org/v2/country/NGA/indicator/NV.IND.MANF.ZS"
params = {"format": "json", "date": "2000:2025", "per_page": 100}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()
payload = response.json()

# Save exactly what the API sent, untouched
out = Path("data/raw/explore_NGA_manufacturing.json")
out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

# Show a quick preview
meta, rows = payload[0], payload[1]
print("Metadata:", meta)
for row in rows[:5]:
    print(row["date"], row["value"])