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

    def _get_cookie_session(self):
        """Helper to load cookies and prepare a session for scraping."""
        if not os.path.exists(self.cookie_file):
            raise Exception("config/cookies.json not found.")

        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1'
        })

        for cookie in cookies_list:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        return session

    def _scrape_groups_via_cookies(self):
        session = self._get_cookie_session()
        
        # Extract c_user from cookies for profile URL
        c_user = next((c.value for c in session.cookies if c.name == 'c_user'), None)
        if not c_user:
             raise Exception("Cookie Error: 'c_user' not found in cookies.json.")

        url = f"https://mbasic.facebook.com/profile.php?id={c_user}&v=groups"
        groups = []
        seen_ids = set()

        print(f"⏳ Starting Cookie Scrape via Profile: {url}")

        while url:
            try:
                resp = session.get(url, timeout=30)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Check Login
                if "log in" in (soup.title.string or "").lower():
                    raise Exception("Cookies Expired. Please update cookies.json.")

                links = soup.find_all('a', href=True)
                for a in links:
                    href = a['href']
                    match = re.search(r'/groups/([^/?&"]+)', href)
                    if match:
                        group_id = match.group(1)
                        if group_id.lower() in ['create', 'search', 'joines', 'feed', 'category', 'discover']:
                            continue
                        
                        name = a.get_text(strip=True) or "Unknown Group"
                        if group_id not in seen_ids:
                            groups.append({'id': group_id, 'name': name})
                            seen_ids.add(group_id)

                next_link = soup.find('a', string=lambda t: t and "See more" in t)
                if next_link:
                    url = next_link['href'] if next_link['href'].startswith('http') else "https://mbasic.facebook.com" + next_link['href']
                    time.sleep(random.uniform(2, 4))
                else:
                    url = None
            except Exception as e:
                print(f"Scraping error: {e}")
                break
        
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        """Attempts API post, falls back to Cookie Scraping on 403."""
        try:
            # --- METHOD 1: GRAPH API ---
            media_ids = []
            for img_path in image_paths:
                url = f"{self.base_url}/{group_id}/photos"
                with open(img_path, 'rb') as img_file:
                    files = {'source': img_file}
                    data = {'access_token': self.access_token, 'published': 'false'}
                    resp = self.session.post(url, data=data, files=files)
                    resp.raise_for_status()
                    media_ids.append(resp.json()['id'])
            
            feed_url = f"{self.base_url}/{group_id}/feed"
            feed_data = {
                'access_token': self.access_token,
                'attached_media': json.dumps([{'media_fbid': mid} for mid in media_ids])
            }
            if caption:
                feed_data['message'] = caption
                
            resp = self.session.post(feed_url, data=feed_data)
            resp.raise_for_status()
            
            # Generate Verification Link
            data = resp.json()
            post_id = data.get('id', '').split('_')[-1]
            permalink = f"https://www.facebook.com/groups/{group_id}/permalink/{post_id}/"
            
            return {"success": True, "link": permalink, "method": "API"}

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"⚠️ API 403 Forbidden for {group_id}. Switching to Cookie Fallback...")
                return self._post_fallback_mbasic(group_id, caption)
            raise e

    def _post_fallback_mbasic(self, group_id, caption):
        """Fallback: Posts text caption via mbasic.facebook.com using cookies."""
        try:
            session = self._get_cookie_session()
            url = f"https://mbasic.facebook.com/groups/{group_id}"
            
            # 1. Get the Group Page to find the form
            resp = session.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 2. Find the Composer Form
            form = soup.find('form', action=lambda x: x and '/composer/mbasic/' in x)
            if not form:
                raise Exception("Could not find posting form on mbasic group page.")
            
            # 3. Extract Hidden Inputs (fb_dtsg, jazoest, etc.)
            data = {}
            for input_tag in form.find_all('input'):
                if input_tag.get('type') == 'hidden':
                    data[input_tag.get('name')] = input_tag.get('value')
            
            # 4. Prepare Payload
            data['body'] = caption or ""
            data['view_post'] = 'Post' # Simulate clicking the Post button
            
            # 5. Submit
            action_url = "https://mbasic.facebook.com" + form['action']
            post_resp = session.post(action_url, data=data)
            post_resp.raise_for_status()
            
            # 6. Return Generic Link (Specific Post ID is hard to get from mbasic redirect)
            return {
                "success": True, 
                "link": f"https://www.facebook.com/groups/{group_id}", 
                "method": "Fallback (Text Only)"
            }
        except Exception as e:
            raise Exception(f"Fallback Failed: {str(e)}")

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
