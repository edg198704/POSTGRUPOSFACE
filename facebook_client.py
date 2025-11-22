import requests
import os
import time
import random
import json
import re
from bs4 import BeautifulSoup

class FacebookClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v19.0"
        self.session = requests.Session()
        self.cookie_file = "config/cookies.json"

    def validate_token(self):
        try:
            params = {'access_token': self.access_token, 'fields': 'id,name'}
            resp = self.session.get(f"{self.base_url}/me", params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"Token Validation Failed: {str(e)}")

    def get_groups(self):
        """Try API first, fallback to Cookies if API fails."""
        try:
            print("Attempting to fetch groups via API...")
            return self._get_groups_api()
        except Exception as e:
            print(f"[WARN] Graph API failed ({str(e)}). Switching to Cookie Scraping...")
            return self._scrape_groups_via_cookies()

    def _get_groups_api(self):
        groups = []
        url = f"{self.base_url}/me/groups"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,privacy',
            'limit': '50'
        }
        while url:
            resp = self.session.get(url, params=params if 'access_token' not in url else None)
            resp.raise_for_status()
            data = resp.json()
            if 'data' in data:
                groups.extend(data['data'])
            url = data.get('paging', {}).get('next')
            params = None
        return groups

    def _scrape_groups_via_cookies(self):
        if not os.path.exists(self.cookie_file):
            raise Exception("API failed and config/cookies.json not found. Please export cookies using EditThisCookie.")

        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        # 1. EXTRACT C_USER (User ID)
        c_user = next((c['value'] for c in cookies_list if c['name'] == 'c_user'), None)
        if not c_user or c_user == "PASTE_VALUE_HERE":
             raise Exception("❌ CONFIG ERROR: 'c_user' cookie is missing or invalid in 'config/cookies.json'.")

        scrape_session = requests.Session()
        
        # Robust Headers
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # 2. TARGET SPECIFIC URL (Profile Groups Tab)
        # This is the Source of Truth for user groups
        url = f"https://mbasic.facebook.com/profile.php?id={c_user}&v=groups"
        groups = []
        seen_ids = set()

        print(f"⏳ Starting Cookie Scrape for User ID: {c_user}...")

        # Helper to parse HTML content
        def parse_html(html_content):
            soup = BeautifulSoup(html_content, 'html.parser')
            found_count = 0
            # 3. ROBUST REGEX
            # Look for links containing /groups/
            links = soup.find_all('a', href=True)
            for a in links:
                href = a['href']
                # Regex to find: /groups/12345 or /groups/mygroup
                # Matches: /groups/12345/?refid... or /groups/mygroup?refid...
                match = re.search(r'/groups/([^/?&"]+)', href)
                if match:
                    group_id = match.group(1)
                    # Filter system pages/keywords
                    if group_id.lower() in ['create', 'search', 'joines', 'feed', 'category', 'discover', 'zk']:
                        continue
                    
                    name = a.get_text(strip=True) or "Unknown Group"

                    if group_id not in seen_ids:
                        groups.append({'id': group_id, 'name': name})
                        seen_ids.add(group_id)
                        found_count += 1
            return soup, found_count

        # Network Scraping Loop
        while url:
            try:
                resp = scrape_session.get(url, timeout=30)
                
                # Check Login/Checkpoint
                if any(x in resp.text.lower() for x in ['log in', 'entrar', 'welcome', 'checkpoint']):
                    with open("debug_mbasic_response.html", "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    raise Exception("Cookies Invalid or Expired. Page title indicates login required.")

                soup, count = parse_html(resp.text)
                print(f"   Found {count} groups on this page.")

                # Pagination
                next_link = soup.find('a', string=lambda t: t and "See more" in t)
                if next_link and next_link.has_attr('href'):
                    url = next_link['href']
                    if not url.startswith('http'):
                        url = "https://mbasic.facebook.com" + url
                    time.sleep(random.uniform(2, 4))
                else:
                    url = None
            except Exception as e:
                print(f"Network error during scraping: {e}")
                break
        
        # 4. THE "NUCLEAR" OPTION (Local HTML Fallback)
        if not groups:
            print("⚠️ Network scraping returned 0 groups. Checking for 'my_groups.html'...")
            if os.path.exists("my_groups.html"):
                try:
                    with open("my_groups.html", "r", encoding="utf-8") as f:
                        local_html = f.read()
                    _, count = parse_html(local_html)
                    print(f"✅ Parsed {count} groups from local file.")
                except Exception as e:
                    print(f"❌ Failed to parse local file: {e}")

        # 5. MANUAL FALLBACK (groups.txt)
        if not groups:
            print("⚠️ Still 0 groups. Checking 'groups.txt'...")
            if os.path.exists("groups.txt"):
                with open("groups.txt", "r") as f:
                    lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    url_match = re.search(r'/groups/([0-9]+|[^/?&"]+)', line)
                    manual_id = url_match.group(1) if url_match else (line.split('/')[-1] if '/' not in line else line)
                    
                    if manual_id and manual_id not in seen_ids:
                        groups.append({'id': manual_id, 'name': f"Manual: {manual_id}"})
                        seen_ids.add(manual_id)
            
        if not groups:
            # Dump debug if truly nothing found
            if 'resp' in locals():
                with open("debug_mbasic_response.html", "w", encoding="utf-8") as f:
                    f.write(resp.text)
            raise Exception("No groups found via Scraping, Local HTML, or groups.txt. Check 'debug_mbasic_response.html'.")
        
        print(f"✅ Total groups available: {len(groups)}")
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        media_ids = []
        # 1. Upload photos as unpublished
        for img_path in image_paths:
            url = f"{self.base_url}/{group_id}/photos"
            with open(img_path, 'rb') as img_file:
                files = {'source': img_file}
                data = {
                    'access_token': self.access_token,
                    'published': 'false'
                }
                resp = self.session.post(url, data=data, files=files)
                resp.raise_for_status()
                media_ids.append(resp.json()['id'])
        
        # 2. Publish to Feed
        feed_url = f"{self.base_url}/{group_id}/feed"
        feed_data = {
            'access_token': self.access_token,
            'attached_media': json.dumps([{'media_fbid': mid} for mid in media_ids])
        }
        if caption:
            feed_data['message'] = caption
            
        resp = self.session.post(feed_url, data=feed_data)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
