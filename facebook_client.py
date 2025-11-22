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

    def _extract_groups_from_html(self, html_content):
        """Robust parsing for both mbasic and desktop HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        groups = []
        seen_ids = set()
        
        # Look for anchor tags with href containing groups
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Regex for both relative and absolute URLs
            # Matches: /groups/123, facebook.com/groups/123, etc.
            match = re.search(r'(?:facebook\.com\/groups\/|\/groups\/)([^/?&"]+)', href)
            if match:
                group_id = match.group(1)
                # Filter out common non-group links
                if group_id.lower() in ['create', 'search', 'joines', 'feed', 'category', 'discover', 'about']:
                    continue
                
                name = a.get_text(strip=True) or "Unknown Group"
                if group_id not in seen_ids:
                    groups.append({'id': group_id, 'name': name})
                    seen_ids.add(group_id)
        return groups

    def _scrape_groups_via_cookies(self):
        if not os.path.exists(self.cookie_file):
            raise Exception("API failed and config/cookies.json not found. Please export cookies using EditThisCookie.")

        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
        
        c_user = None
        for cookie in cookies_list:
            if cookie.get('value') == "PASTE_VALUE_HERE":
                raise Exception("❌ CONFIG ERROR: Replace 'PASTE_VALUE_HERE' in cookies.json.")
            if cookie.get('name') == 'c_user':
                c_user = cookie.get('value')
        
        if not c_user:
            raise Exception("❌ Cookie Error: 'c_user' not found.")

        scrape_session = requests.Session()
        scrape_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1'
        })

        for cookie in cookies_list:
            scrape_session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        url = f"https://mbasic.facebook.com/profile.php?id={c_user}&v=groups"
        groups = []
        seen_ids = set()

        print(f"⏳ Starting Cookie Scrape via Profile: {url}")

        while url:
            try:
                resp = scrape_session.get(url, timeout=30)
            except Exception as e:
                print(f"Network error during scraping: {e}")
                break

            # Use robust extraction
            new_groups = self._extract_groups_from_html(resp.text)
            for g in new_groups:
                if g['id'] not in seen_ids:
                    groups.append(g)
                    seen_ids.add(g['id'])

            soup = BeautifulSoup(resp.text, 'html.parser')
            if any(x in (soup.title.string.lower() if soup.title else "") for x in ['log in', 'entrar', 'welcome', 'checkpoint']):
                raise Exception("Cookies Invalid or Expired.")

            next_link = soup.find('a', string=lambda t: t and "See more" in t)
            if next_link and next_link.has_attr('href'):
                url = next_link['href']
                if not url.startswith('http'):
                    url = "https://mbasic.facebook.com" + url
                time.sleep(random.uniform(2, 4))
            else:
                url = None
        
        if not groups:
            # Fallback to local file parsing if network scraping fails
            # 1. Try HTML dump if available
            if os.path.exists("groups.html"):
                 print("📂 Parsing local groups.html...")
                 with open("groups.html", "r", encoding="utf-8") as f:
                     groups = self._extract_groups_from_html(f.read())
            
            # 2. Try TXT list
            elif os.path.exists("groups.txt"):
                print("📂 Parsing local groups.txt...")
                with open("groups.txt", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            groups.append({'id': line.split('/')[-1], 'name': f"Manual: {line}"})
        
        return groups

    def post_images(self, group_id, image_paths, caption=None):
        try:
            # 1. Try Graph API
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
            if caption: feed_data['message'] = caption
                
            resp = self.session.post(feed_url, data=feed_data)
            resp.raise_for_status()
            
            # Generate Verification Link
            post_id = resp.json().get('id', '').split('_')[-1]
            return f"https://www.facebook.com/groups/{group_id}/permalink/{post_id}/"

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"⚠️ API 403 Forbidden for {group_id}. Switching to Cookie Fallback...")
                return self._post_via_cookies(group_id, caption, image_paths)
            raise e

    def _post_via_cookies(self, group_id, caption, image_paths):
        if not os.path.exists(self.cookie_file):
            raise Exception("Cookies not found for fallback.")
            
        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
            
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1'
        })
        for c in cookies_list:
            session.cookies.set(c['name'], c['value'], domain=c['domain'])

        # 1. Get Group Page
        url = f"https://mbasic.facebook.com/groups/{group_id}"
        resp = session.get(url)
        if 'login' in resp.url:
             raise Exception("Cookies expired (Login detected).")

        soup = BeautifulSoup(resp.text, 'html.parser')
        form = soup.find('form', action=re.compile(r'/composer/mbasic/'))
        
        if not form:
            raise Exception("Could not find Write Post form on mbasic.")

        action_url = "https://mbasic.facebook.com" + form['action']
        data = {}
        for inp in form.find_all('input', type='hidden'):
            data[inp.get('name')] = inp.get('value')

        data['xc_message'] = caption if caption else ""
        
        if image_paths:
            data['xc_message'] += "\n\n(Image upload skipped in fallback mode)"

        submit_btn = form.find('input', type='submit')
        if submit_btn and submit_btn.get('name'):
            data[submit_btn.get('name')] = submit_btn.get('value')

        post_resp = session.post(action_url, data=data)
        post_resp.raise_for_status()
        
        return f"https://www.facebook.com/groups/{group_id}"

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
