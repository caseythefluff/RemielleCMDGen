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

# Target categories updated to their endpoints
urls = [
    "https://zzz.gachabase.net/agents/beta",
    "https://zzz.gachabase.net/w-engines/beta",
    "https://zzz.gachabase.net/bangboo/beta",
    "https://zzz.gachabase.net/drive-discs/beta",
    "https://zzz.gachabase.net/items/all/beta",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

extracted_data = {"agents": [], "wengines": [], "bangboos": [], "discs": [], "items": []}
seen_ids = {"agents": set(), "wengines": set(), "bangboos": set(), "discs": set(), "items": set()}

for url in urls:
    category_key = ""
    url_path_category = ""
    if "agents" in url:
        category_key = "agents"
        url_path_category = "agents"
    elif "w-engines" in url:
        category_key = "wengines"
        url_path_category = "w-engines"
    elif "bangboo" in url:
        category_key = "bangboos"
        url_path_category = "bangboo"
    elif "drive-discs" in url:
        category_key = "discs"
        url_path_category = "drive-discs"
    elif "items" in url:
        category_key = "items"
        url_path_category = "items"

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
                    
                name = item_slug.replace("-", " ").replace("_", " ").title()
                
                # Directly target the exact <img> tag structure containing the Gachabase CDN source
                img_matches = []
                for m in re.finditer(r'<img[^>]+src=["\'](https?://i\.gachabase\.net/[^"\']+)["\']', window, re.IGNORECASE):
                    distance = abs(m.start() - slug_pos_in_window)
                    img_matches.append((m.group(1), distance))
                
                # Fallback backup search if the img tag uses protocol-relative paths or alternative attribute orders
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
print("🎉 Successfully parsed all categories with exact img tag matching!")
print("==========================================")
