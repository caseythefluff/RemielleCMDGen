import json
import re
import urllib.request

# Target categories following your exact structure
urls = [
    "https://zzz.gachabase.net/agents",
    "https://zzz.gachabase.net/w-engines",
    "https://zzz.gachabase.net/bangboo/beta",
    "https://zzz.gachabase.net/drive-discs/",
    "https://zzz.gachabase.net/items/all/",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

extracted_data = {"agents": [], "wengines": [], "bangboos": [], "discs": [], "items": []}

for url in urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")

            # Pattern to match cards/containers containing both the asset link and its icon image source
            # Gachabase stores optimized thumbnails via i.gachabase.net
            
            # Let's find blocks or use a combined pattern matching nearby img tags or srcsets
            # We look for href patterns and extract any image src/srcset containing i.gachabase.net near it
            
            # Splitting HTML roughly by item card elements or parsing via regex groups
            # Universal pattern looking for chunks containing a target link and an image source
            
            # Alternative: Search for patterns where an <a> link includes an <img> tag
            card_pattern = r'<a[^>]*href="([^"]*/(\d+)/([^"/]+)/?)"[^>]*>(.*?)</a>'
            cards = re.findall(card_pattern, html, re.DOTALL)

            for full_link, item_id, item_slug, inner_html in cards:
                name = item_slug.replace("-", " ").title()
                
                # Extract icon URL from the inner card HTML (looking for i.gachabase.net or common image attributes)
                img_match = re.search(r'src="([^"]*i\.gachabase\.net[^"]+)"', inner_html)
                if not img_match:
                    # Check srcset or data-src if standard src isn't direct
                    img_match = re.search(r'srcset="([^"\s]+)', inner_html)
                
                icon_url = img_match.group(1) if img_match else ""
                
                # Clean up proxy image formatting if necessary or keep full gachabase CDN link
                if icon_url and not icon_url.startswith("http"):
                    icon_url = f"https://zzz.gachabase.net{icon_url}"

                entry = {
                    "id": item_id,
                    "name": name,
                    "url": full_link if full_link.startswith("http") else f"https://zzz.gachabase.net{full_link}",
                    "icon": icon_url
                }

                # Categorize based on path type
                if "agents" in url and entry not in extracted_data["agents"]:
                    extracted_data["agents"].append(entry)
                elif "w-engines" in url and entry not in extracted_data["wengines"]:
                    extracted_data["wengines"].append(entry)
                elif "bangboo" in url and entry not in extracted_data["bangboos"]:
                    extracted_data["bangboos"].append(entry)
                elif "drive-discs" in url and entry not in extracted_data["discs"]:
                    extracted_data["discs"].append(entry)
                elif "items" in url and entry not in extracted_data["items"]:
                    extracted_data["items"].append(entry)

    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

# Save the parsed data to a JSON file containing IDs, Names, Sublinks, and Icons
with open("gachabase_sync.json", "w") as f:
    json.dump(extracted_data, f, indent=4)

print("Successfully parsed entities and grabbed their CDN icons!")
