import requests
import os
import json
import re
from bs4 import BeautifulSoup

class FacebookClient:
    def __init__(self, access_token=None):
        # Token is optional now as we rely on cookies
        self.access_token = access_token
        self.session = requests.Session()
        self.cookie_file = "config/cookies.json"
        self._load_cookies()

    def _load_cookies(self):
        if not os.path.exists(self.cookie_file):
            raise Exception("config/cookies.json not found.")
        
        with open(self.cookie_file, 'r') as f:
            cookies_list = json.load(f)
            
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1'
        })
        
        for cookie in cookies_list:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', '.facebook.com'))

    def post_via_mbasic(self, group_id, message):
        """
        Posts text to a group using mbasic.facebook.com to bypass API restrictions.
        """
        # 1. Navigate to Group Page
        url = f"https://mbasic.facebook.com/groups/{group_id}"
        print(f"Navigating to {url}...")
        resp = self.session.get(url)
        
        if 'login' in resp.url or 'checkpoint' in resp.url:
            raise Exception("Cookies expired or checkpoint hit.")

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 2. Find the Composer Form
        # The form action usually contains '/composer/mbasic/'
        form = soup.find('form', action=re.compile(r'/composer/mbasic/'))
        if not form:
            # Debug: Save HTML if form not found
            with open("debug_no_form.html", "w", encoding="utf-8") as f: f.write(resp.text)
            raise Exception("Could not find posting form on mbasic page.")

        # 3. Extract Hidden Inputs (fb_dtsg, jazoest, target, etc.)
        data = {}
        for inp in form.find_all('input', type='hidden'):
            if inp.get('name') and inp.get('value'):
                data[inp.get('name')] = inp.get('value')

        # 4. Add Message Payload
        data['xc_message'] = message
        data['view_post'] = 'Post'  # The submit button name

        # 5. Submit POST
        action_url = "https://mbasic.facebook.com" + form['action']
        post_resp = self.session.post(action_url, data=data)
        post_resp.raise_for_status()
        
        return post_resp.url
