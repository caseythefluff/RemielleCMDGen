import json
import re
import urllib.request
import urllib.parse

# Custom handler to force Python's urllib to seamlessly follow HTTP 308 Permanent Redirects
class HTTP308RedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_301(req, fp, code, msg, headers)

# Install the custom redirect handler globally
opener = urllib.request.build_opener(HTTP308RedirectHandler)
urllib.request.install_opener(opener)

urls = [
    ("https://zzz.gachabase.net/agents/beta?lang=en", "agents", "agents"),
    ("https://zzz.gachabase.net/w-engines/beta?lang=en", "wengines", "w-engines"),
    ("https://zzz.gachabase.net/bangboo/beta?lang=en", "bangboos", "bangboo"),
    ("https://zzz.gachabase.net/drive-discs/beta?lang=en", "discs", "drive-discs"),
    ("https://zzz.gachabase.net/items/all/beta?lang=en", "items", "items/all"),
    ("https://zzz.gachabase.net/items/currencies/beta?lang=en", "items", "items/currencies"),
    ("https://zzz.gachabase.net/items/materials/beta?lang=en", "items", "items/materials"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

extracted_data = {"agents": [], "wengines": [], "bangboos": [], "discs": [], "items": []}
seen_ids = {key: set() for key in extracted_data.keys()}

global_agent_ids = set()

# First pass: Pre-scan agents to build the global exclusion filter
for url, category_key, url_path_category in urls:
    if category_key != "agents":
        continue
        
    print(f"\n🔍 Pre-scanning Agents to build exclusion filter...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
            html = html.replace('\\u002F', '/').replace('\\/', '/')
            html = urllib.parse.unquote(html)

            for match in re.finditer(r'["\']?slug["\']?\s*:\s*["\']([^"\']+)["\']', html, re.IGNORECASE):
                item_slug = match.group(1)
                if item_slug.lower() in ['beta', 'page', 'lang', 'en', 'all', 'currencies', 'materials']:
                    continue
                start = max(0, match.start() - 1000)
                end = min(len(html), match.end() + 1000)
                window = html[start:end]
                slug_pos_in_window = match.start() - start
                
                id_matches = []
                for m in re.finditer(r'["\']?id["\']?\s*:\s*["\']?(\d+)["\']?', window, re.IGNORECASE):
                    distance = abs(m.start() - slug_pos_in_window)
                    id_matches.append((m.group(1), distance))
                
                if id_matches:
                    item_id = min(id_matches, key=lambda x: x[1])[0]
                    global_agent_ids.add(item_id)
    except Exception as e:
        print(f"❌ Failed pre-scan: {e}")

print(f"Locked in {len(global_agent_ids)} agent IDs to filter out from other sections.")

# Second pass: Process all categories
for url, category_key, url_path_category in urls:
    print(f"\n==========================================")
    print(f"🔍 Scanning Category: {category_key.upper()} ({url_path_category})")
    print(f"==========================================")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
            
            html = html.replace('\\u002F', '/').replace('\\/', '/')
            html = urllib.parse.unquote(html)

            slug_matches = list(re.finditer(r'["\']?slug["\']?\s*:\s*["\']([^"\']+)["\']', html, re.IGNORECASE))
            print(f"Found {len(slug_matches)} raw slugs in HTML stream.")

            for match in slug_matches:
                item_slug = match.group(1)
                
                if item_slug.lower() in ['beta', 'page', 'lang', 'en', 'all', 'home', 'privacy', 'about', 'discord', 'currencies', 'materials']:
                    continue
                    
                start = max(0, match.start() - 1000)
                end = min(len(html), match.end() + 1000)
                window = html[start:end]
                slug_pos_in_window = match.start() - start
                
                # Find the closest ID
                id_matches = []
                for m in re.finditer(r'["\']?(?:item_id|id)["\']?\s*:\s*["\']?(\d+)["\']?', window, re.IGNORECASE):
                    match_id_str = m.group(1)
                    distance = abs(m.start() - slug_pos_in_window)
                    
                    # Apply strict check for Bangboos and Items to avoid grabbing 1-digit rarity numbers
                    if category_key == "bangboos":
                        if len(match_id_str) == 5 and match_id_str.startswith("5"):
                            id_matches.append((match_id_str, distance))
                    elif category_key == "items":
                        # Items generally have IDs that are 3 digits or longer (e.g. 111, 103040)
                        if len(match_id_str) >= 3:
                            id_matches.append((match_id_str, distance))
                    else:
                        id_matches.append((match_id_str, distance))
                
                if not id_matches:
                    continue
                
                item_id = min(id_matches, key=lambda x: x[1])[0]
                
                if item_id in seen_ids[category_key]:
                    continue

                # Universal bleed check: If this ID belongs to an agent, skip it unless we are parsing agents
                if category_key != "agents" and item_id in global_agent_ids:
                    continue

                # Reverted structural validation rules for other categories
                if category_key == "wengines":
                    if not (item_id.startswith("14") or "test-engine" in item_slug.lower()):
                        continue
                elif category_key == "discs":
                    if not (item_id.startswith("31") or int(item_id) > 30000):
                        continue

                name = item_slug.replace("-", " ").replace("_", " ").title()
                
                # Extract image CDN URL from the Svelte element structure
                img_matches = []
                for m in re.finditer(r'<img[^>]+src=["\'](https?://i\.gachabase\.net/[^"\']+)["\']', window, re.IGNORECASE):
                    distance = abs(m.start() - slug_pos_in_window)
                    img_matches.append((m.group(1), distance))
                
                if not img_matches:
                    for m in re.finditer(r'src=["\'](https?://i\.gachabase\.net/[^"\']+)["\']', window, re.IGNORECASE):
                        distance = abs(m.start() - slug_pos_in_window)
                        img_matches.append((m.group(1), distance))

                icon_url = ""
                if img_matches:
                    icon_url = min(img_matches, key=lambda x: x[1])[0]
                    print(f"  ✅ [{item_id}] {name} -> Icon found: {icon_url}")
                else:
                    print(f"  ⚠️ [{item_id}] {name} -> NO icon matched in window!")

                # Since url_path_category now matches the exact route (e.g. "items/currencies"), it constructs perfectly
                full_url = f"https://zzz.gachabase.net/{url_path_category}/{item_id}/{item_slug}/beta?lang=en"
                
                entry = {
                    "id": item_id,
                    "name": name,
                    "url": full_url,
                    "icon": icon_url
                }
                
                extracted_data[category_key].append(entry)
                seen_ids[category_key].add(item_id)

    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")

with open("gachabase_sync.json", "w") as f:
    json.dump(extracted_data, f, indent=4)

print("\n==========================================")
print("🎉 Successfully parsed all categories with targeted subdirectories!")
print("==========================================")
