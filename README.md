# Kuma_Reddit
A personal project Sub-Reddit for scraping images with the ability to send the images to a discord channel. Simply add or remove entries from `self._subreddits` and it will handle the rest. 

It will handle gallery submissions from a subreddit too!

# Requirements
- You will need to a Reddit User Account and an Reddit App Token.
- You will need a Webhook URL which can be achieved via Discord Channel Settings -> Integrations -> Webhooks.
- You can use a `CRON TAB` via Linux to keep it constantly running pointing at the `Kuma.bash` script.
    - It will check the `PID` and keep the script constantly running.
    - check the log file if needed.
- reddit_token.py file with the below contents.
    - reddit_secret
    - reddit_client_id
    - reddit_username
    - reddit_password
    - webhook_url

# Example
**![Example](/resources/kuma_reddit_example.png)**