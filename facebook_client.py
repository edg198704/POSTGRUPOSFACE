import requests
import os
import time
import random
import json
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
            raise Exception("API failed and config/cookies.json not found. Please create it using the template.")

        with open(self.cookie_file, 'r') as f:
            try:
                cookies_list = json.load(f)
            except json.JSONDecodeError:
                raise Exception("config/cookies.json is not valid JSON.")
        
        # CRITICAL: Check for placeholders
        for cookie in cookies_list:
            if cookie.get('value') in ["PASTE_VALUE_HERE", "REPLACE_ME"]:
                raise Exception(f"❌ Placeholder detected in cookies.json for '{cookie.get('name')}'. Please open Chrome DevTools -> Application -> Cookies, copy the values for 'c_user' and 'xs', and paste them into config/cookies.json.")

        scrape_session = requests.Session()
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        url = "https://mbasic.facebook.com/groups/?seemore"
        groups = []
        seen_ids = set()

        print("⏳ Starting Cookie Scrape...")

        while url:
            resp = scrape_session.get(url)
            if "login" in resp.url or resp.status_code != 200:
                if not groups:
                    raise Exception("Cookies expired or invalid (redirected to login). Please re-export cookies from Chrome.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all group links in mbasic
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/groups/' in href:
                    try:
                        # Extract ID safely from /groups/12345/?refid=...
                        parts = href.split('/groups/')
                        if len(parts) > 1:
                            id_part = parts[1].split('/')[0].split('?')[0]
                            if id_part.isdigit() and id_part not in seen_ids:
                                name = a.get_text().strip()
                                if name:
                                    groups.append({'id': id_part, 'name': name})
                                    seen_ids.add(id_part)
                    except Exception:
                        continue
            
            # Pagination: Find 'See more' link
            next_link = soup.find('a', string=lambda t: t and "See more" in t)
            if next_link and next_link.has_attr('href'):
                url = next_link['href']
                if not url.startswith('http'):
                    url = "https://mbasic.facebook.com" + url
                time.sleep(random.uniform(1, 2))
            else:
                url = None
        
        if not groups:
            raise Exception("No groups found via scraping. Check if your account has groups or if cookies are valid.")
        
        print(f"✅ Scraped {len(groups)} groups via cookies.")
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        # 1. Upload photos as unpublished (published=false) to get media IDs
        media_ids = []
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
        
        # 2. Publish to Feed with attached_media
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
