"""
Mirrors your own X posts to a Telegram channel.

Checks for new posts since the last run (tracked in .last_tweet_id),
mirrors text + photos (videos/GIFs get a text note + link back to the
original post, since Telegram's Bot API can't easily re-upload X's video
delivery format). Respects `dry_run` in config.yaml.

Required env vars:
  X_BEARER_TOKEN       (App-only bearer token from your X Developer app —
                         read-only access is enough, no OAuth1 needed)
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID     (e.g. "@YourChannelName")
"""
import os
import sys
import requests
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
STATE_PATH = os.path.join(os.path.dirname(__file__), ".last_tweet_id")

X_API = "https://api.x.com/2"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def x_headers():
    return {"Authorization": f"Bearer {os.environ['X_BEARER_TOKEN']}"}


def get_user_id(username):
    r = requests.get(f"{X_API}/users/by/username/{username}", headers=x_headers(), timeout=20)
    r.raise_for_status()
    return r.json()["data"]["id"]


def get_last_id():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return f.read().strip() or None
    return None


def save_last_id(tweet_id):
    with open(STATE_PATH, "w") as f:
        f.write(str(tweet_id))


def fetch_new_tweets(user_id, since_id, cfg):
    exclude = []
    if not cfg.get("include_replies", False):
        exclude.append("replies")
    if not cfg.get("include_retweets", False):
        exclude.append("retweets")

    params = {
        "max_results": 20,
        "tweet.fields": "created_at,attachments",
        "expansions": "attachments.media_keys",
        "media.fields": "url,type,preview_image_url",
    }
    if exclude:
        params["exclude"] = ",".join(exclude)
    if since_id:
        params["since_id"] = since_id

    r = requests.get(f"{X_API}/users/{user_id}/tweets", headers=x_headers(), params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    tweets = data.get("data", [])
    media_lookup = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}

    # API returns newest-first; mirror oldest-first so channel order matches posting order
    tweets.reverse()
    return tweets, media_lookup


def send_to_telegram(text, photo_urls, video_note, dry_run):
    if dry_run:
        print(f"[DRY RUN] Would mirror to Telegram:\n{text}")
        if photo_urls:
            print(f"  + {len(photo_urls)} photo(s)")
        if video_note:
            print(f"  + video/gif note: {video_note}")
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    full_text = text + (f"\n\n{video_note}" if video_note else "")

    if not photo_urls:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": full_text},
            timeout=20,
        )
    elif len(photo_urls) == 1:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            json={"chat_id": chat_id, "photo": photo_urls[0], "caption": full_text},
            timeout=20,
        )
    else:
        media = [{"type": "photo", "media": url} for url in photo_urls]
        media[0]["caption"] = full_text
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMediaGroup",
            json={"chat_id": chat_id, "media": media},
            timeout=20,
        )

    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    print(f"Mirrored tweet -> Telegram OK")


def main():
    cfg = load_config()
    username = cfg["x_username"]

    user_id = get_user_id(username)
    since_id = get_last_id()
    tweets, media_lookup = fetch_new_tweets(user_id, since_id, cfg)

    if not tweets:
        print("No new posts to mirror.")
        return

    highest_id = since_id
    for tweet in tweets:
        text = tweet["text"]
        photo_urls = []
        video_note = None

        for key in tweet.get("attachments", {}).get("media_keys", []):
            media = media_lookup.get(key)
            if not media:
                continue
            if media["type"] == "photo":
                photo_urls.append(media["url"])
            elif media["type"] in ("video", "animated_gif"):
                video_note = f"[video/GIF — see original: https://x.com/{username}/status/{tweet['id']}]"

        send_to_telegram(text, photo_urls, video_note, cfg.get("dry_run", True))

        if highest_id is None or int(tweet["id"]) > int(highest_id):
            highest_id = tweet["id"]

    if highest_id and not cfg.get("dry_run", True):
        save_last_id(highest_id)


if __name__ == "__main__":
    main()
