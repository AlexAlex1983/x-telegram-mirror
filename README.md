# X → Telegram Mirror Bot

Watches your own X account and mirrors new posts (text + photos) to a
Telegram channel within ~15 minutes. Videos/GIFs get a text note with a
link back to the original post instead of being re-uploaded (Telegram's
Bot API can't easily pull X's video delivery format).

Ships in **dry-run mode** — logs what it would mirror without posting,
until you turn that off.

## Setup

### 1. Get your X Bearer Token
- Go to [developer.x.com](https://developer.x.com) → your app (or create
  one, same process as before) → Keys and tokens → find "Bearer Token"
  under "Authentication Tokens" → generate/copy it. This is read-only
  access — no need for OAuth 1.0a keys here since this bot never posts
  to X, only reads your own timeline.
- Note: this uses the same pay-per-use billing as posting does — reading
  tweets costs a small amount per request too. At every-15-minutes
  polling, that's ~96 checks/day; keep an eye on the balance same as
  your other bots.

### 2. Set `x_username` in config.yaml
Open `config.yaml`, replace `YOUR_X_USERNAME_HERE` with your actual X
handle (no @).

### 3. Create a Telegram bot and channel
- Message **@BotFather** on Telegram → `/newbot` → save the token.
- Create a channel (or use an existing one) → Administrators → Add Admin
  → add your bot → enable "Post Messages".

### 4. Push this folder to a GitHub repo
Same process as the other bots — new repo, upload these files (use
"creating a new file" with the full path `.github/workflows/mirror.yml`
so it lands in the right folder).

### 5. Add repository secrets
Settings → Secrets and variables → Actions → add: `X_BEARER_TOKEN`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (your channel's @username).

### 6. Test it
Actions tab → "Mirror X to Telegram" → Run workflow. Check the log for
`[DRY RUN] Would mirror to Telegram:` followed by your actual recent
post(s).

### 7. Go live
Once it looks right, set `dry_run: false` in `config.yaml`, commit. From
here it checks every 15 minutes and mirrors anything new.

## Notes
- First run: since there's no `.last_tweet_id` yet, it'll try to mirror
  your last ~20 posts. If you don't want a backlog dump on first launch,
  let it run once in dry-run mode, then manually create a `.last_tweet_id`
  file containing your most recent post's ID before going live — that
  way it only picks up posts made after that point.
- Excludes replies and retweets by default (only mirrors your own
  original posts) — change `include_replies` / `include_retweets` in
  `config.yaml` if you want those mirrored too.
