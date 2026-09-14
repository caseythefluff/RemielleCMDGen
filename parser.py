import json
import re
import urllib.request

# Target the specific beta sections where listings are fully exposed
urls = [
    ("https://zzz.gachabase.net/agents/beta", "agents"),
    ("https://zzz.gachabase.net/w-engines/beta?lang=en", "wengines"),
    ("https://zzz.gachabase.net/bangboo/beta?lang=en", "bangboos"),
    ("https://zzz.gachabase.net/drive-discs/beta", "discs"),
    ("https://zzz.gachabase.net/items/all/beta?lang=en", "items"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

extracted_data = {"agents": [], "wengines": [], "bangboos": [], "discs": [], "items": []}

for url, category in urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")

            # Match links following your exact structure: /type/ID/name/
            # e.g., /agents/1641/phoenix/beta or similar subpaths
            pattern = r'href="([^"]*/(\d+)/([^"/]+)(?:/[^"]*)?)"'
            matches = re.findall(pattern, html)

            seen_ids = set()
            for full_link, item_id, item_slug in matches:
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                name = item_slug.replace("-", " ").title()
                
                # Look for an accompanying icon source near the link in raw text chunks
                # Default to empty string if not directly parsed via plain text anchor
                icon_url = ""
                
                full_url = full_link if full_link.startswith("http") else f"https://zzz.gachabase.net{full_link}"

                entry = {
                    "id": item_id,
                    "name": name,
                    "url": full_url,
                    "icon": icon_url
                }

                if category in extracted_data:
                    extracted_data[category].append(entry)

        print(f"Successfully scraped {category}: found {len(extracted_data[category])} items.")

    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

# Save the parsed data to the sync file
with open("gachabase_sync.json", "w") as f:
    json.dump(extracted_data, f, indent=4)

print("Parser run complete!")
