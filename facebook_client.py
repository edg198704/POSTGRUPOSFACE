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
        """Initialize session with headers and cookies."""
        # MANDATORY HEADER CONFIGURATION for Samsung S23 Bypass
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
                        if c.get('value') != "PASTE_VALUE_HERE":
                            self.session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.facebook.com'))
            except Exception as e:
                print(f"[WARN] Failed to load cookies: {e}")

    def post_via_mbasic(self, group_id, message):
        """
        Posts text to a group using mbasic.facebook.com simulation.
        Bypasses Graph API 403 errors and 'Unsupported Browser' blocks.
        """
        if not os.path.exists(self.cookie_file):
            raise Exception("cookies.json missing! Cannot use mbasic fallback.")

        # 1. Navigate to Group Page to get the form
        url = f"https://mbasic.facebook.com/groups/{group_id}"
        print(f"[MBASIC] Navigating to {url}...")
        resp = self.session.get(url)
        
        # Check for common blocks
        if 'login' in resp.url or 'checkpoint' in resp.url:
            raise Exception("Cookies expired or checkpoint hit. Please refresh cookies.json")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Check if we are on the "Error" or "Unsupported Browser" page
        page_title = soup.title.string if soup.title else "No Title"
        if "Error" in page_title or "Facebook Lite" in resp.text:
             # Log the specific error context
             with open("debug_browser_block.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
             raise Exception(f"Blocked by Facebook (Title: {page_title}). Headers may need rotation. Saved debug_browser_block.html")

        # 2. Find the Composer Form
        # Look for form with action containing '/composer/mbasic/'
        form = soup.find('form', action=re.compile(r'/composer/mbasic/'))
        if not form:
            # Debug: Save HTML to see what happened
            with open("debug_failed_form.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            raise Exception(f"Could not find post form on group page '{page_title}'. Check debug_failed_form.html")

        # 3. Extract Hidden Inputs (fb_dtsg, jazoest, target, etc.)
        data = {}
        for inp in form.find_all('input', type='hidden'):
            data[inp.get('name')] = inp.get('value')

        # Verify critical tokens
        if 'fb_dtsg' not in data:
             with open("debug_missing_tokens.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
             raise Exception("fb_dtsg token not found in form. Saved debug_missing_tokens.html")

        # 4. Add Message Payload
        data['xc_message'] = message
        data['view_post'] = 'Post'
        
        # Handle the submit button specifically if needed
        submit_btn = form.find('input', type='submit')
        if submit_btn and submit_btn.get('name'):
            data[submit_btn.get('name')] = submit_btn.get('value')

        # 5. Submit POST
        action_url = "https://mbasic.facebook.com" + form['action']
        print(f"[MBASIC] Submitting to {action_url}...")
        
        # Update Referer for the POST request to match the group page
        self.session.headers.update({'Referer': url})
        
        post_resp = self.session.post(action_url, data=data)
        post_resp.raise_for_status()

        # 6. Validation
        # Usually redirects to the group page or a permalink view
        if post_resp.status_code == 200:
            return f"https://www.facebook.com/groups/{group_id}"
        else:
            raise Exception(f"Post failed with status {post_resp.status_code}")

    @staticmethod
    def get_random_sleep(min_sec=30, max_sec=90):
        return random.randint(min_sec, max_sec)
