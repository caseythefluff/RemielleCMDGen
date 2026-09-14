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
    ("https://zzz.gachabase.net/agents/beta", "agents", "agents"),
    ("https://zzz.gachabase.net/w-engines/beta", "wengines", "w-engines"),
    ("https://zzz.gachabase.net/bangboo/beta", "bangboos", "bangboo"),
    ("https://zzz.gachabase.net/drive-discs/beta", "discs", "drive-discs"),
    ("https://zzz.gachabase.net/items/all/beta", "items", "items"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

extracted_data = {"agents": [], "wengines": [], "bangboos": [], "discs": [], "items": []}
seen_ids = {key: set() for key in extracted_data.keys()}

for url, category_key, url_path_category in urls:
    print(f"\n==========================================")
    print(f"🔍 Scanning Category: {category_key.upper()}")
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
                
                if item_slug.lower() in ['beta', 'page', 'lang', 'en', 'all', 'home', 'privacy', 'about', 'discord']:
                    continue
                    
                start = max(0, match.start() - 1000)
                end = min(len(html), match.end() + 1000)
                window = html[start:end]
                slug_pos_in_window = match.start() - start
                
                # Find the closest ID
                id_matches = []
                for m in re.finditer(r'["\']?id["\']?\s*:\s*["\']?(\d+)["\']?', window, re.IGNORECASE):
                    distance = abs(m.start() - slug_pos_in_window)
                    id_matches.append((m.group(1), distance))
                
                if not id_matches:
                    continue
                
                item_id = min(id_matches, key=lambda x: x[1])[0]
                
                if item_id in seen_ids[category_key]:
                    continue

                # STRICT BOUNDARY GUARD: Prevent cross-category bleeding (e.g. Agents leaking into W-Engines)
                # Allow test engines explicitly as requested
                if category_key == "wengines":
                    # W-Engine IDs usually start with '14' or contain 'test-engine'
                    if not (item_id.startswith("14") or "test-engine" in item_slug.lower()):
                        continue
                elif category_key == "agents":
                    # Agents usually start with '10' or '16'
                    if not (item_id.startswith("10") or item_id.startswith("16")):
                        continue
                elif category_key == "bangboos":
                    # Bangboos usually have short IDs or specific ranges, ensure we don't grab agents/w-engines here
                    if item_id.startswith("10") or item_id.startswith("14"):
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

                full_url = f"https://zzz.gachabase.net/{url_path_category}/{item_id}/{item_slug}/beta"
                
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
print("🎉 Successfully parsed with category guards intact!")
print("==========================================")
