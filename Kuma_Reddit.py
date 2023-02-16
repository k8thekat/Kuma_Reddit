#!/usr/bin/env python3 

import praw
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

from pprint import pprint

class Kuma_Reddit():
    def __init__(self, dev: bool=False, dev_subreddit: str= None) -> None:
        self._webhook_url = reddit_token.webhook_url
        self._json = 'reddit.json'
        self._url_list = []
        self._hash_list = []

        self._submission_limit = 30
        self._User_Agent = UserAgent().chrome
        self._pytz = pytz.timezone('US/Pacific')

        self._subreddits = ['awwnime', 'wallpaper', 'himecut', 'pantsu', 'ecchi', 'EcchiSkirts',
                      'KuroiHada', 'Nekomimi', 'pantsu', 'Sukebei', 'waifusgonewild', 'HentaiAI']
        
        self._reddit = praw.Reddit(
            client_id=reddit_token.reddit_client_id,
            client_secret=reddit_token.reddit_secret,
            user_agent="Linux:https://github.com/k8thekat/Kuma_Kuma:dev (by /u/Kuma_Kuma_bear)"
        )

        last_check = self.json_load()
        #Testing Purpose..
        if dev:
            #self.subreddit_inspector(subreddit= "awwnime")
            dev_time = timedelta(hours= 1)
            self.subreddit_media_handler(last_check= (last_check - dev_time))
            return
        
        self.check_loop(last_check= last_check)

    def json_load(self):
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

    def subreddit_inspector(self, subreddit: str):
        cur_subreddit = self._reddit.subreddit(subreddit)
        for submission in cur_subreddit.new(limit= 5):
            #print(submission.title)
            #if hasattr(submission, media_metadata):
                #submission_images = [img for img in submission.media_metadata]
                #for img in submission_images:
                    #if img["e"] != 'Image':
                        #continue
                    #save img["s"]
                        
            #if submission.title == "[1920×1080] Fire Force S1 ED1 FHD Screen Caps [ZIP DOWNLOAD LINK]":
                #print(dir(submission))
            attrs = [entry for entry in (dir(submission))]
            for entry in attrs:
                if entry.startswith('__') or entry.startswith('_'):
                    continue
                print('Attr name', entry)
                attr_data = getattr(submission, entry)
                print(attr_data)
                #submission.media_metadata
                if entry == "media_metadata":
                    #print(attr_data)
                    for key in attr_data:
                        print(attr_data[key], "\n")
                        if attr_data[key]["e"] == 'Image':
                            print('found image')
                                
                #print()
            
    def subreddit_media_handler(self, last_check: datetime):
        """Iterates through the subReddits Submissions and sends media_metadata"""
        for sub in self._subreddits:
            cur_subreddit = self._reddit.subreddit(sub)
            count = 0
            # limit - controls how far back to go (true limit is 100 entries)
            for submission in cur_subreddit.new(limit= 5): #self._submission_limit
                post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                found_post = False
                print(f'Checking subreddit {sub} -> submission title: {submission.title} submission post_time: {post_time.astimezone(self._pytz).ctime()} last_check: {last_check.astimezone(self._pytz).ctime()}')

                if post_time >= last_check:  # The more recent time will be greater than..
                    #Usually submissions with multiple images will be using this `attr`
                    if hasattr(submission, "media_metadata"):
                        print('Found media_metadata')
                        #pprint(submission.media_metadata.items())
                        #submission_images = [img for img in submission.media_metadata]

                        for key, img in submission.media_metadata.items():
                            #print('image', img)
                            #example {'status': 'valid', 'e': 'Image', 'm': 'image/jpg', 'p': [lists of random resolution images], 's': LN 149}
                            #This allows us to only get Images.
                            if img["e"] != 'Image':
                                continue
                            
                            #example 's': {'y': 2340, 'x': 1080, 'u': 'https://preview.redd.it/0u8xnxknijha1.jpg?width=1080&format=pjpg&auto=webp&v=enabled&s=04e505ade5889f6a5f559dacfad1190446607dc4'}, 'id': '0u8xnxknijha1'}
                            img_url = img["s"]["u"]
                            #Verify the URL is not already in my sent list.
                            if img_url not in self._url_list:
                                self._url_list.append(img_url)
                                status = self.hash_process(img_url)

                                if status:
                                    found_post = True
                                    count =+ 1
                                    self.webhook_send(content= f'**r/{sub}** ->  __{submission.title}__\n{img_url}\n')
                                    time.sleep(1) #Soft buffer delay between sends to prevent rate limiting.

                    elif hasattr(submission, "url_overridden_by_dest"):
                        print('Found url_overridden_by_dest')
                        img_url = submission.url_overridden_by_dest

                        if img_url not in self._url_list:
                            self._url_list.append(img_url)
                            status = self.hash_process(img_url)

                            if status:
                                found_post = True
                                count =+ 1
                                self.webhook_send(content= f'**r/{sub}** ->  __{submission.title}__\n{img_url}\n')
                                time.sleep(1) #Soft buffer delay between sends to prevent rate limiting.
                    
                    else:
                        continue

            if found_post == False:
                print(f'No new Submissions in {sub} since {last_check.ctime()}')

        return count

    def hash_process(self, img_url: str):
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
        
    def subreddit_handler(self, last_check: datetime):
        """Iterates through the subReddits Submissions and sends url_overriden_by_dest."""
        for sub in self._subreddits:
            cur_subreddit = self._reddit.subreddit(sub)
            count = 0
            # limit - controls how far back to go (true limit is 100 entries)
            for submission in cur_subreddit.new(limit= self._submission_limit):
                post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                found_post = False
                print(f'Checking subreddit {sub} -> submission title: {submission.title} submission post_time: {post_time.astimezone(self._pytz).ctime()} last_check: {last_check.astimezone(self._pytz).ctime()}')

                if post_time >= last_check:  # The more recent time will be greater than..
                    #If a submission doesn't have a url. Skip it.
                    if not hasattr(submission, "url_overridden_by_dest"):
                        continue

                    elif submission.url_overridden_by_dest not in self._url_list:
                        self._url_list.append(submission.url_overridden_by_dest)
                        req = urllib.request.Request(url= submission.url_overridden_by_dest, headers= {'User-Agent': str(self._User_Agent)})

                        try:
                            req_open = urllib.request.urlopen(req)
                        except Exception as e:
                            print(f'Unable to handle {submission.url_overridden_by_dest} with error: {e}')
                            continue

                        # This only gets "Images" and not "Videos" -> content_type() returns something like 'image/jpeg' or 'text/html'
                        if 'image' in req_open.headers.get_content_type():
                            my_hash = hashlib.sha256(req_open.read()).hexdigest()
                            if my_hash in self._hash_list:
                                continue

                            self._hash_list.append(my_hash)
                            found_post = True
                            count =+ 1
                            self.webhook_send(content= f'**r/{sub}** ->  __{submission.title}__ \n{submission.url_overridden_by_dest}\n')
                            time.sleep(1) #Soft buffer delay between sends to prevent rate limiting.
                               
                        else:  # Failed to find a 'image'
                            print(f'submission title: {submission.title} is not an image -> {req_open.headers.get_content_type()}')

            if found_post == False:
                print(f'No new Submissions in {sub} since {last_check.ctime()}')

        return count

    def webhook_send(self, content: str, username: str = "Kuma Bear of Reddit"):
        """Sends the Data to the Discord webhook"""
        data = {"content": content, "username": username}
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
                #count = self.subreddit_handler(last_check= last_check)
                count = self.subreddit_media_handler(last_check= last_check)
                last_check = cur_time
                self.json_save(last_check= last_check)

                if count >= 1:
                    print(f'Finished Sending {str(count) + "Images" if count > 1 else str(count) + "Image"}')
            else:
                print(f'Sleeping for {delay*30} seconds or {delay*0.5} minutes')
                time.sleep(delay*30)

#Kuma_Reddit(dev = True, dev_subreddit= "wallpaper")
Kuma_Reddit()
