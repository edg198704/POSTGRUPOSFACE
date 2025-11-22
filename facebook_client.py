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
        
        # VALIDATION: Check for placeholders
        for cookie in cookies_list:
            if cookie.get('value') == "PASTE_VALUE_HERE":
                raise Exception("❌ CONFIG ERROR: You must open 'config/cookies.json' and replace 'PASTE_VALUE_HERE' with your actual 'c_user' and 'xs' cookie values from Chrome.")

        scrape_session = requests.Session()
        # FIX: Add robust User-Agent to prevent blocking
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://mbasic.facebook.com/'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        url = "https://mbasic.facebook.com/groups/?seemore"
        groups = []
        seen_ids = set()
        
        # FIX: Regex pattern to extract Group ID or Alias from URL
        # Matches /groups/12345/ or /groups/some.alias/
        group_pattern = re.compile(r'/groups/([^/?#]+)')

        print("⏳ Starting Cookie Scrape...")

        while url:
            try:
                resp = scrape_session.get(url, timeout=30)
            except Exception as e:
                print(f"❌ Network error: {e}")
                break

            # Check if redirected to login (cookies invalid)
            if "login" in resp.url or "Mw==" in resp.text: # Mw== is often in login page source
                if not groups:
                    # Dump HTML for debugging
                    with open("debug_mbasic_response.html", "w", encoding="utf-8") as f:
                        f.write(resp.text)
                    raise Exception("Cookies expired or invalid (Redirected to Login). HTML saved to debug_mbasic_response.html")
                break

            # Use lxml if available, else html.parser
            try:
                soup = BeautifulSoup(resp.text, 'lxml')
            except:
                soup = BeautifulSoup(resp.text, 'html.parser')
            
            # FIX: Scan ALL <a> tags using Regex
            links = soup.find_all('a', href=True)
            found_on_page = False
            
            for a in links:
                href = a['href']
                match = group_pattern.search(href)
                if match:
                    group_id = match.group(1)
                    
                    # Filter out system links that might match the pattern
                    if group_id.lower() in ['create', 'category', 'joingroups', 'discover', 'search']:
                        continue
                        
                    if group_id not in seen_ids:
                        name = a.get_text().strip()
                        if name:
                            groups.append({'id': group_id, 'name': name})
                            seen_ids.add(group_id)
                            found_on_page = True
            
            # Pagination: Look for "See more"
            next_link = soup.find('a', string=lambda t: t and "See more" in t)
            if next_link and next_link.has_attr('href'):
                url = next_link['href']
                if not url.startswith('http'):
                    url = "https://mbasic.facebook.com" + url
                time.sleep(random.uniform(1.5, 3.0)) # Polite delay
            else:
                url = None
        
        if not groups:
            # FIX: Mandatory HTML Dump on failure
            with open("debug_mbasic_response.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print("❌ No groups found. Raw HTML saved to 'debug_mbasic_response.html'.")
            print("👉 Please open this file in a browser to check if you are logged in or blocked.")
            raise Exception("No groups found via scraping. Check debug_mbasic_response.html")
        
        print(f"✅ Scraped {len(groups)} groups via cookies.")
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
