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
        self._init_session()

    def _init_session(self):
        """Initialize session with strict headers to bypass browser blocking."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://mbasic.facebook.com',
            'Referer': 'https://mbasic.facebook.com/',
            'Upgrade-Insecure-Requests': '1'
        })
        self._load_cookies()

    def _load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r') as f:
                    cookies_list = json.load(f)
                    for c in cookies_list:
                        if c.get('value') and c.get('value') != "PASTE_VALUE_HERE":
                            self.session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.facebook.com'))
            except Exception as e:
                print(f"[WARN] Failed to load cookies: {e}")

    def post_via_mbasic(self, group_id, message):
        """
        Posts text to a group using mbasic.facebook.com simulation.
        """
        if not os.path.exists(self.cookie_file):
            raise Exception("cookies.json missing! Cannot use mbasic fallback.")

        # 1. Navigate to Group Page
        url = f"https://mbasic.facebook.com/groups/{group_id}"
        print(f"[MBASIC] Navigating to {url}...")
        resp = self.session.get(url)
        
        # Check for block/interstitial
        if "Facebook is not available on this browser" in resp.text or "Download Facebook Lite" in resp.text:
             with open("debug_browser_block.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
             raise Exception("Browser Blocked: Headers failed to bypass Lite interstitial. See debug_browser_block.html")

        if 'login' in resp.url or 'checkpoint' in resp.url:
            with open("debug_login_redirect.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            raise Exception("Cookies expired or checkpoint hit. See debug_login_redirect.html")

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 2. Find the Composer Form
        # We look for the input named 'fb_dtsg' to confirm it's a valid form context
        form = None
        for f in soup.find_all('form'):
            if f.find('input', {'name': 'fb_dtsg'}):
                form = f
                break
        
        if not form:
            # Fallback: look for action containing composer
            form = soup.find('form', action=re.compile(r'/composer/mbasic/'))

        if not form:
            with open("debug_failed_form.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            raise Exception(f"Could not find post form in group {group_id}. Saved HTML to debug_failed_form.html")

        # 3. Extract Hidden Inputs
        data = {}
        for inp in form.find_all('input'):
            if inp.get('name'):
                data[inp.get('name')] = inp.get('value', '')

        # 4. Add Message Payload
        data['xc_message'] = message
        data['view_post'] = 'Post'

        # 5. Submit POST
        action = form.get('action')
        if not action.startswith('http'):
            action_url = "https://mbasic.facebook.com" + action
        else:
            action_url = action

        print(f"[MBASIC] Submitting to {action_url}...")
        
        # Add Referer for the POST
        self.session.headers.update({'Referer': url})
        
        post_resp = self.session.post(action_url, data=data)
        
        # 6. Validation
        if post_resp.status_code == 200:
            return f"https://www.facebook.com/groups/{group_id}"
        else:
            with open("debug_post_fail.html", "w", encoding="utf-8") as f:
                f.write(post_resp.text)
            raise Exception(f"Post failed with status {post_resp.status_code}")

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
