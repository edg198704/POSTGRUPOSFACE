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
        try:
            return self._get_groups_api()
        except Exception as e:
            print(f"[WARN] Graph API failed ({str(e)}). Attempting Cookie Fallback...")
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

        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        scrape_session = requests.Session()
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        url = "https://mbasic.facebook.com/groups/?seemore"
        resp = scrape_session.get(url)
        
        if "login" in resp.url or resp.status_code != 200:
            raise Exception("Cookies expired or invalid. Please re-export cookies.")

        soup = BeautifulSoup(resp.text, 'html.parser')
        groups = []
        seen_ids = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/groups/' in href:
                try:
                    parts = href.split('/groups/')
                    if len(parts) > 1:
                        group_id = parts[1].split('/')[0].split('?')[0]
                        if group_id.isdigit() and group_id not in seen_ids:
                            name = a.get_text().strip()
                            if name:
                                groups.append({'id': group_id, 'name': name})
                                seen_ids.add(group_id)
                except Exception:
                    continue
        
        if not groups:
            raise Exception("No groups found via scraping.")
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        # 1. Upload photos with published=false to get IDs
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
    def sleep_random(min_sec=30, max_sec=90):
        time.sleep(random.randint(min_sec, max_sec))
