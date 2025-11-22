import requests
import os
import time
import random
import json
frombs4 import BeautifulSoup

class FacebookClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v19.0"
        self.session = requests.Session()
        # Ensure correct path to cookies
        self.cookie_file = os.path.join(os.getcwd(), "config", "cookies.json")

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
            # Try API First
            return self._get_groups_api()
        except Exception as e:
            print(f"[WARN] API Failed: {e}. Switching to Cookie Scraper.")
            return self._scrape_groups_via_cookies()

    def _get_groups_api(self):
        groups = []
        url = f"{self.base_url}/me/groups"
        params = {'access_token': self.access_token, 'limit': '50', 'fields': 'id,name'}
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
            raise Exception(f"Cookies file not found at {self.cookie_file}. Please export cookies to this file.")

        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
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

        while url:
            resp = scrape_session.get(url)
            if "login" in resp.url:
                raise Exception("Cookies expired. Please re-export cookies.json")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Parse Groups
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/groups/' in href:
                    # Extract ID from /groups/12345/ or /groups/12345?ref=...
                    try:
                        parts = href.split('/groups/')[1].split('/')[0].split('?')[0]
                        if parts.isdigit() and parts not in seen_ids:
                            groups.append({'id': parts, 'name': a.get_text().strip()})
                            seen_ids.add(parts)
                    except:
                        pass
            
            # Pagination: Find 'See more' link
            next_a = soup.find('a', string=lambda t: t and "See more" in t)
            if next_a:
                url = next_a['href']
                if not url.startswith('http'):
                    url = "https://mbasic.facebook.com" + url
                time.sleep(random.uniform(1, 2))
            else:
                url = None
                
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        # 1. Upload Unpublished Photos to get IDs
        media_ids = []
        for img_path in image_paths:
            url = f"{self.base_url}/{group_id}/photos"
            with open(img_path, 'rb') as f:
                files = {'source': f}
                data = {'access_token': self.access_token, 'published': 'false'}
                resp = self.session.post(url, data=data, files=files)
                resp.raise_for_status()
                media_ids.append(resp.json()['id'])
        
        # 2. Publish Feed Post with Attachments
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

    def sleep_random(self, min_s=30, max_s=60):
        s = random.randint(min_s, max_s)
        time.sleep(s)
        return s
