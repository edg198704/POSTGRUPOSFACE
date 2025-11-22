import requests
import os
import time
import random
import json
from bs4 import BeautifulSoup

class FacebookClient:
    def __init__(self, access_token):
        if not access_token:
            # Allow empty token if only using cookies, but warn
            pass
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
            # If token fails, we might still be able to scrape, but for now return a dummy or raise
            # For dashboard compatibility, we raise, but the dashboard handles exceptions.
            raise Exception(f"Token Validation Failed: {str(e)}")

    def get_groups(self):
        # Step 1: Try API
        try:
            return self._get_groups_api()
        except Exception as e:
            print(f"[WARN] Graph API failed ({str(e)}). Attempting Cookie Fallback...")
            # Step 2: Try Cookies
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
            raise Exception("API failed and config/cookies.json not found. Please export cookies.")

        # Load Cookies
        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        scrape_session = requests.Session()
        # Mimic a real browser
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # Fetch mbasic groups page
        url = "https://mbasic.facebook.com/groups/?seemore"
        print(f"[INFO] Scraping {url}...")
        resp = scrape_session.get(url)
        
        if "login" in resp.url or resp.status_code != 200:
            raise Exception("Cookies expired or invalid. Please re-export cookies from Chrome.")

        soup = BeautifulSoup(resp.text, 'html.parser')
        groups = []
        seen_ids = set()

        # Parse Anchor tags looking for /groups/<id>
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Typical pattern: /groups/123456789/?refid=...
            if '/groups/' in href:
                try:
                    # Extract ID
                    parts = href.split('/groups/')
                    if len(parts) > 1:
                        group_id = parts[1].split('/')[0].split('?')[0]
                        
                        # Validate ID is numeric
                        if group_id.isdigit() and group_id not in seen_ids:
                            name = a.get_text().strip()
                            if name:
                                groups.append({
                                    'id': group_id,
                                    'name': name,
                                    'privacy': 'scraped' # Metadata not available in simple scrape
                                })
                                seen_ids.add(group_id)
                except Exception:
                    continue
        
        if not groups:
            raise Exception("No groups found via scraping. Check cookie validity or language settings.")
            
        return groups

    def post_photo(self, group_id, image_path, caption=None):
        # Note: Posting still attempts API first. 
        # Full cookie-based posting would require a much larger refactor (payload extraction).
        # We assume the user might have posting permissions but not listing permissions, or this is a partial fix.
        url = f"{self.base_url}/{group_id}/photos"
        try:
            with open(image_path, 'rb') as img_file:
                files = {'source': img_file}
                data = {'access_token': self.access_token}
                if caption:
                    data['message'] = caption
                
                resp = self.session.post(url, data=data, files=files)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            raise Exception(f"Failed to post to group {group_id}: {str(e)}")

    @staticmethod
    def sleep_random(min_sec=30, max_sec=90):
        time.sleep(random.randint(min_sec, max_sec))
