#!/usr/bin/env python3 
'''
   Copyright (C) 2021-2022 Katelynn Cadwallader.

   This file is part of Kuma_Reddit.

   Kuma_Reddit is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3, or (at your option)
   any later version.

   Kuma_Reddit is distributed in the hope that it will be useful, but WITHOUT
   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
   or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
   License for more details.

   You should have received a copy of the GNU General Public License
   along with Kuma_Reddit; see the file COPYING.  If not, write to the Free
   Software Foundation, 51 Franklin Street - Fifth Floor, Boston, MA
   02110-1301, USA. 
'''
import praw
from praw.models import Subreddit
import sys
import reddit_token
import requests
import time
from datetime import datetime, timezone, timedelta
import json
import hashlib
import urllib.request
import urllib.error
import pytz
from fake_useragent import UserAgent
import tzlocal
from typing import Union

class Kuma_Reddit():
    def __init__(self) -> None:
        self._webhook_url = reddit_token.webhook_url
        self._json = 'reddit.json'
        self._url_list = []
        self._hash_list = []
        self._url_prefixs:tuple[str, ...] = ("http://", "https://")

        #This is how many posts in each subreddit the script will look back.
        #By default the subreddit script looks at subreddits in `NEW` listing order.
        self._submission_limit = 30
        self._User_Agent = UserAgent().chrome

        #This forces the timezone to change based upon your OS for better readability in your prints()
        #This script uses `UTC` for functionality purposes.
        self._system_tz = tzlocal.get_localzone()
        #Need to use the string representation of the time zone for `pytz` eg. `America/Los_Angeles`
        self._pytz = pytz.timezone(str(self._system_tz))

        #Purely used to fill out the user_agent parameter of PRAW
        self._sysos = sys.platform.title()
        self._user = reddit_token.reddit_username.title()

        #Feel free to change the User Name to suite you.
        self._user_name = "Kuma Bear of Reddit"

        #Simply place a string match of the subreddit `/r/sub` into this list.
        self._subreddits = ['awwnime', 'AnimeLingerie', 'wallpaper', 'himecut', 'pantsu', 'ecchi', 'EcchiSkirts',
                      'KuroiHada', 'Nekomimi', 'pantsu', 'Sukebei', 'waifusgonewild', 'HentaiAI']#, 'Hentai'] #Too many posts in this subreddit
        
        self._reddit = praw.Reddit(
            client_id=reddit_token.reddit_client_id,
            client_secret=reddit_token.reddit_secret,
            user_agent= f"{self._sysos}:https://github.com/k8thekat/Kuma_Reddit: (by /u/{self._user if self._user_name == None else self._user_name})"
        )

        last_check = self.json_load()
        self.check_loop(last_check= last_check)

    def json_load(self):
        last_check: datetime = datetime.now(tz=timezone.utc)
        with open(self._json, "r") as jfile:
            data = json.load(jfile)
            print('Loaded our settings...')

        if 'last_check' in data:
            if data['last_check'] == 'None':
                last_check = datetime.now(tz=timezone.utc)
            else:
                last_check = datetime.fromtimestamp(
                    data['last_check'], tz=timezone.utc)
            print('Last Check... Done.')

        if 'url_list' in data:
            self._url_list = data['url_list']
            print('URL List... Done.')

        if 'hash_list' in data:
            self._hash_list = data['hash_list']
            print('Hash List... Done.')
        jfile.close()
        return last_check

    def json_save(self, last_check: datetime):
        #I generate an upper limit of the list based upon the subreddits times the submissin search limit; this allows for configuration changes and not having to scale the limit of the list
        limiter = (len(self._subreddits) * self._submission_limit) * 3

        if len(self._url_list) > limiter: 
            print(f'Trimming down url list...')
            self._url_list = self._url_list[len(self._url_list) - limiter:]

        if len(self._hash_list) > limiter:
            print(f'Trimming down hash list...')
            self._hash_list = self._hash_list[len(self._hash_list) - limiter:]

        data = {
            "last_check": last_check.timestamp(),
            "url_list": self._url_list,
            "hash_list": self._hash_list
        }
        with open(self._json, "w") as jfile:
            json.dump(data, jfile)
            print('Saving our settings...')
            jfile.close()
            
    def subreddit_media_handler(self, last_check: datetime):
        """Iterates through the subReddits Submissions and sends media_metadata"""
        count = 0
        found_post = False
        img_url: Union[str, None] = None

        for sub in self._subreddits:
            cur_subreddit: Subreddit = self._reddit.subreddit(sub)
            # limit - controls how far back to go (true limit is 100 entries)
            for submission in cur_subreddit.new(limit= self._submission_limit): #self._submission_limit
                post_time: datetime = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                found_post = False
                print(f'Checking subreddit {sub} -> submission title: {submission.title} submission post_time: {post_time.astimezone(self._pytz).ctime()} last_check: {last_check.astimezone(self._pytz).ctime()}')

                if post_time >= last_check:  # The more recent time will be greater than..
                    #Usually submissions with multiple images will be using this `attr`
                    if hasattr(submission, "media_metadata"):
                        #print('Found media_metadata')

                        for key, img in submission.media_metadata.items():
                            #example {'status': 'valid', 'e': 'Image', 'm': 'image/jpg', 'p': [lists of random resolution images], 's': LN 105}
                            #This allows us to only get Images.
                            if "e" in img and img["e"] == 'Image':
                                #example 's': {'y': 2340, 'x': 1080, 'u': 'https://preview.redd.it/0u8xnxknijha1.jpg?width=1080&format=pjpg&auto=webp&v=enabled&s=04e505ade5889f6a5f559dacfad1190446607dc4'}, 'id': '0u8xnxknijha1'}
                                img_url = img["s"]["u"]
                                   
                            else:
                                continue

                    elif hasattr(submission, "url_overridden_by_dest"):
                        #print('Found url_overridden_by_dest')
                        img_url = submission.url_overridden_by_dest
                        if not img_url.startswith(self._url_prefixs):
                            continue
        
                    else:
                        continue

                    if img_url != None:
                        if img_url in self._url_list:
                            continue

                        self._url_list.append(img_url)
                        status: bool = self.hash_process(img_url)

                        if status:
                            found_post = True
                            count += 1
                            self.webhook_send(content= f'**r/{sub}** ->  __{submission.title}__\n{img_url}\n')
                            time.sleep(1) #Soft buffer delay between sends to prevent rate limiting.

            if found_post == False:
                print(f'No new Submissions in {sub} since {last_check.ctime()}')

        return count

    def hash_process(self, img_url: str) -> bool:
        """Checks the Hash of the supplied url against our hash list."""
        req = urllib.request.Request(url= img_url, headers= {'User-Agent': str(self._User_Agent)})

        try:
            req_open = urllib.request.urlopen(req)
        except Exception as e:
            print(f'Unable to handle {img_url} with error: {e}')
            return False

        # This only gets "Images" and not "Videos" -> content_type() returns something like 'image/jpeg' or 'text/html'  
        if 'image' in req_open.headers.get_content_type():
            my_hash = hashlib.sha256(req_open.read()).hexdigest()
            if my_hash not in self._hash_list:
                self._hash_list.append(my_hash)
                return True
            
            else:
                print('Found a duplicate hash...')
                return False 
        else:  # Failed to find a 'image'
            print(f'URL: {img_url} is not an image -> {req_open.headers.get_content_type()}')  
            return False                    

    def webhook_send(self, content: str):
        """Sends the Data to the Discord webhook"""
        data = {"content": content, "username": self._user if self._user_name == None else self._user_name}
        result = requests.post(self._webhook_url, json=data)
        if 200 <= result.status_code < 300:
            print(f"Webhook sent {result.status_code}")
        else:
            print(f"Not sent with {result.status_code}, response:\n{result.json()}")

    def check_loop(self, last_check: datetime):
        delay = 30
        diff_time = timedelta(minutes= delay)
        while (1):
            cur_time = datetime.now(tz=timezone.utc)
            print(f'Checking the time...Cur_time: {cur_time.astimezone(self._pytz).ctime()} last_time: {last_check.astimezone(self._pytz).ctime()} diff_time: {(cur_time - diff_time).astimezone(self._pytz).ctime()}')

            if cur_time - diff_time >= last_check:
                print('Times up...checking subreddits')
                count = self.subreddit_media_handler(last_check= last_check)
                last_check = cur_time
                self.json_save(last_check= last_check)

                if count >= 1:
                    print(f'Finished Sending {str(count) + " Images" if count > 1 else str(count) + " Image"}')
            else:
                print(f'Sleeping for {delay*30} seconds or {delay*0.5} minutes')
                time.sleep(delay*30)

Kuma_Reddit()
