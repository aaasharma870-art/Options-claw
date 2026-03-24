# Cron Setup for GEX Regime Engine

## Local (macOS/Linux)

Run every 30 minutes during market hours (9:30 AM - 4:00 PM ET):

```bash
# Edit crontab
crontab -e

# Add this line (adjust path):
*/30 9-15 * * 1-5 cd /path/to/Options-claw && python tier1_webhooks/gex_regime_engine.py >> /tmp/gex_cron.log 2>&1
```

## DigitalOcean Droplet

1. Create a $4/mo droplet (smallest is fine — this is just HTTP calls)
2. Clone the repo and install dependencies:

```bash
git clone https://github.com/aaasharma870-art/Options-claw.git
cd Options-claw
pip install httpx
```

3. Create `.env` with your API keys:

```bash
cp .env.template .env
nano .env
# Add: POLYGON_API_KEY=your-polygon-key
# Add: ANTHROPIC_API_KEY=your-anthropic-key  (only needed for Tier 3)
```

4. Set up webhook URLs in `tier1_webhooks/webhook_config.json`

5. Add cron job:

```bash
crontab -e
# GEX regime check every 30 min during market hours (ET = UTC-5)
*/30 14-20 * * 1-5 cd /root/Options-claw && python3 tier1_webhooks/gex_regime_engine.py >> /var/log/gex.log 2>&1
```

## Cost

- DigitalOcean droplet: $4/month
- Polygon.io free tier: 5 API calls/minute (plenty for every-30-min checks)
- OA webhooks: Free
- **Total: $4/month** (vs $20-40/day with Computer Use)
