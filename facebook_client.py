import requests
import os
import time
import random

class FacebookClient:
    def __init__(self, access_token):
        if not access_token:
            raise ValueError("Access Token is required")
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v19.0"
        self.session = requests.Session()

    def validate_token(self):
        try:
            params = {'access_token': self.access_token, 'fields': 'id,name'}
            resp = self.session.get(f"{self.base_url}/me", params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"Token Validation Failed: {str(e)}")

    def get_groups(self):
        groups = []
        url = f"{self.base_url}/me/groups"
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,privacy',
            'limit': '50'
        }
        
        while url:
            try:
                resp = self.session.get(url, params=params if 'access_token' not in url else None)
                resp.raise_for_status()
                data = resp.json()
                
                if 'data' in data:
                    groups.extend(data['data'])
                
                # Pagination: Facebook provides the full next URL
                url = data.get('paging', {}).get('next')
                # Clear params for next iteration as they are in the url
                params = None
            except Exception as e:
                raise Exception(f"Error fetching groups: {str(e)}")
        return groups

    def post_photo(self, group_id, image_path, caption=None):
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
