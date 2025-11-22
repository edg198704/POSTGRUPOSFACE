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
        params = {'access_token': self.access_token, 'fields': 'id,name'}
        resp = self.session.get(f"{self.base_url}/me", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_groups(self):
        try:
            return self._get_groups_api()
        except Exception as e:
            print(f"[WARN] API Failed ({e}). Using Cookie Scraper...")
            return self._scrape_groups_via_cookies()

    def _get_groups_api(self):
        groups = []
        url = f"{self.base_url}/me/groups"
        params = {'access_token': self.access_token, 'fields': 'id,name', 'limit': '50'}
        while url:
            resp = self.session.get(url, params=params if 'access_token' not in url else None)
            resp.raise_for_status()
            data = resp.json()
            if 'data' in data: groups.extend(data['data'])
            url = data.get('paging', {}).get('next')
            params = None
        return groups

    def _scrape_groups_via_cookies(self):
        if not os.path.exists(self.cookie_file):
            raise Exception("cookies.json not found.")
        
        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        s = requests.Session()
        s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        for c in cookies_list:
            s.cookies.set(c['name'], c['value'], domain=c['domain'])
            
        resp = s.get("https://mbasic.facebook.com/groups/?seemore")
        if "login" in resp.url: raise Exception("Cookies expired.")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        groups = []
        seen = set()
        
        for a in soup.find_all('a', href=True):
            if '/groups/' in a['href']:
                try:
                    gid = a['href'].split('/groups/')[1].split('/')[0].split('?')[0]
                    if gid.isdigit() and gid not in seen:
                        groups.append({'id': gid, 'name': a.get_text().strip()})
                        seen.add(gid)
                except: continue
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        # 1. Upload photos as unpublished to get IDs
        media_ids = []
        for path in image_paths:
            url = f"{self.base_url}/{group_id}/photos"
            with open(path, 'rb') as img:
                data = {'access_token': self.access_token, 'published': 'false'}
                files = {'source': img}
                resp = self.session.post(url, data=data, files=files)
                resp.raise_for_status()
                media_ids.append(resp.json()['id'])
        
        # 2. Publish to Feed
        if not media_ids: return
        
        url = f"{self.base_url}/{group_id}/feed"
        attached_media = [{'media_fbid': mid} for mid in media_ids]
        data = {
            'access_token': self.access_token,
            'attached_media': json.dumps(attached_media)
        }
        if caption: data['message'] = caption
        
        resp = self.session.post(url, data=data)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def sleep_random(min_sec=30, max_sec=90):
        time.sleep(random.randint(min_sec, max_sec))
