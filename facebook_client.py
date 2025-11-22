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
        self.base_url = "https://mbasic.facebook.com"
        self.session = requests.Session()
        self.cookie_file = "config/cookies.json"
        self._init_session()

    def _init_session(self):
        """Initialize session with Desktop headers to bypass mobile app enforcement."""
        # STRICT HEADERS: Impersonate Desktop Chrome to avoid 'Download App' redirects
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://mbasic.facebook.com',
            'Referer': 'https://mbasic.facebook.com/',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive'
        })
        self._load_cookies()

    def _load_cookies(self):
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r') as f:
                    cookies_list = json.load(f)
                    for c in cookies_list:
                        if c.get('value') != "PASTE_VALUE_HERE":
                            self.session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.facebook.com'))
            except Exception as e:
                print(f"[WARN] Failed to load cookies: {e}")

    def post_via_mbasic(self, group_id, message):
        """
        Posts text to a group using mbasic.facebook.com simulation.
        Uses Desktop UA to avoid 'Download Facebook Lite' blocks.
        """
        if not os.path.exists(self.cookie_file):
            raise Exception("cookies.json missing! Cannot use mbasic fallback.")

        # 1. Navigate to Group Page
        url = f"https://mbasic.facebook.com/groups/{group_id}"
        print(f"[MBASIC] Navigating to {url}...")
        resp = self.session.get(url)
        
        # Check for login redirects
        if 'login' in resp.url or 'checkpoint' in resp.url:
            raise Exception("Cookies expired or checkpoint hit. Please refresh cookies.json")
        
        # 2. Check for Block (Facebook Lite / Not Available)
        page_text_lower = resp.text.lower()
        if "facebook lite" in page_text_lower or "facebook no está disponible" in page_text_lower:
            with open(f"debug_block_{group_id}.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            raise Exception("Blocked by Facebook (Mobile App Enforced). Check cookies or User-Agent.")

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 3. Find Form (Robust Strategy)
        # First, try finding the form by action regex (legacy method)
        form = soup.find('form', action=re.compile(r'/composer/mbasic/'))
        
        # If not found, search specifically for the hidden input 'fb_dtsg' and get its parent form
        if not form:
            dtsg_input = soup.find('input', {'name': 'fb_dtsg'})
            if dtsg_input:
                form = dtsg_input.find_parent('form')
        
        # If still not found, dump debug and raise error
        if not form:
            debug_filename = f"debug_no_form_{group_id}.html"
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"Saved debug HTML. Open {debug_filename} to see what the bot saw.")
            raise Exception(f"Could not find post form. Saved {debug_filename}")

        # 4. Extract Inputs
        data = {}
        for inp in form.find_all('input', type='hidden'):
            if inp.get('name'):
                data[inp.get('name')] = inp.get('value')

        # Validation: Ensure fb_dtsg is present
        if 'fb_dtsg' not in data:
             # Try to find it again inside the form if missed (unlikely with hidden check)
             dtsg_input = form.find('input', {'name': 'fb_dtsg'})
             if dtsg_input:
                 data['fb_dtsg'] = dtsg_input.get('value')
             else:
                 raise Exception("fb_dtsg token missing from form inputs.")

        # 5. Prepare Payload
        data['xc_message'] = message
        data['view_post'] = 'Post'
        
        # Handle submit button (sometimes required)
        submit_btn = form.find('input', type='submit')
        if submit_btn and submit_btn.get('name'):
            data[submit_btn.get('name')] = submit_btn.get('value')

        # 6. Submit POST
        action_url = "https://mbasic.facebook.com" + form['action']
        
        # Update Referer to match the group page we are on
        self.session.headers.update({'Referer': url})
        
        print(f"[MBASIC] Submitting to {action_url}...")
        post_resp = self.session.post(action_url, data=data)
        post_resp.raise_for_status()

        # 7. Validation
        if post_resp.status_code == 200:
            return f"https://www.facebook.com/groups/{group_id}"
        else:
            raise Exception(f"Post failed with status {post_resp.status_code}")

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
