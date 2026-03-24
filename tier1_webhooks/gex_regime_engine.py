"""GEX Regime Classification Engine.

Standalone Python script that:
1. Fetches options data from Polygon.io (or Tradier)
2. Calculates Gamma Exposure (GEX) for SPY
3. Classifies market regime (POSITIVE_GEX / NEGATIVE_GEX / TRANSITIONAL)
4. Triggers the appropriate OA webhook

Designed to run on cron: every 30 minutes during market hours.
No Docker, no browser, no AI — just pure Python + HTTP.

Usage:
    python gex_regime_engine.py                     # Run once
    python gex_regime_engine.py --dry-run           # Calculate but don't trigger
    python gex_regime_engine.py --symbol AAPL       # Different symbol
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tier1_webhooks.webhook_manager import WebhookManager

log = logging.getLogger("options-claw.gex")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# GEX regime thresholds
GEX_POSITIVE_THRESHOLD = 0.5   # Billions — above this = positive GEX
GEX_NEGATIVE_THRESHOLD = -0.5  # Below this = negative GEX
# Between thresholds = TRANSITIONAL


def get_polygon_api_key() -> str:
    """Load Polygon.io API key from environment or .env."""
    key = os.environ.get("POLYGON_API_KEY")
    if key:
        return key

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("POLYGON_API_KEY="):
                return line.split("=", 1)[1].strip()

    raise RuntimeError("POLYGON_API_KEY not found. Set it in environment or .env")


async def fetch_options_chain(symbol: str, api_key: str) -> list[dict]:
    """Fetch current options chain from Polygon.io.

    Returns list of contracts with greeks.
    """
    import httpx

    url = f"https://api.polygon.io/v3/snapshot/options/{symbol}"
    params = {
        "apiKey": api_key,
        "limit": 250,
        "order": "asc",
        "sort": "expiration_date",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    return data.get("results", [])


def calculate_gex(options_data: list[dict], spot_price: float) -> float:
    """Calculate net Gamma Exposure (GEX) in billions.

    GEX = sum(gamma * open_interest * contract_multiplier * spot^2 / 1e9)
    Calls contribute positive gamma, puts contribute negative gamma.
    """
    total_gex = 0.0
    contract_multiplier = 100  # Standard options contract

    for contract in options_data:
        greeks = contract.get("greeks", {})
        gamma = greeks.get("gamma", 0)
        oi = contract.get("open_interest", 0)
        contract_type = contract.get("details", {}).get("contract_type", "")

        if gamma == 0 or oi == 0:
            continue

        # GEX contribution
        gex_contribution = gamma * oi * contract_multiplier * (spot_price ** 2) / 1e9

        if contract_type == "put":
            gex_contribution = -gex_contribution  # Puts have negative GEX contribution

        total_gex += gex_contribution

    return total_gex


def classify_regime(gex_value: float) -> str:
    """Classify market regime based on GEX.

    Returns:
        "POSITIVE_GEX" — Market is sticky, range-bound. Trade Iron Condors.
        "NEGATIVE_GEX" — Trends accelerate. Trade directional spreads.
        "TRANSITIONAL" — No clear structure. Reduce risk.
    """
    if gex_value > GEX_POSITIVE_THRESHOLD:
        return "POSITIVE_GEX"
    elif gex_value < GEX_NEGATIVE_THRESHOLD:
        return "NEGATIVE_GEX"
    else:
        return "TRANSITIONAL"


async def run_classification(symbol: str = "SPY", dry_run: bool = False):
    """Full pipeline: fetch data -> calculate GEX -> classify -> trigger webhook."""

    log.info(f"GEX Regime Engine starting for {symbol}")

    # Check if market is open (basic check)
    now = datetime.now(timezone.utc)
    hour_et = (now.hour - 5) % 24  # Rough UTC -> ET conversion
    if hour_et < 9 or hour_et >= 16:
        log.info("Market appears closed. Skipping.")
        return

    # Fetch options data
    try:
        api_key = get_polygon_api_key()
        log.info("Fetching options chain from Polygon.io...")
        options_data = await fetch_options_chain(symbol, api_key)
        log.info(f"Fetched {len(options_data)} contracts")
    except RuntimeError as e:
        log.error(str(e))
        log.info("To use this engine, get a free API key from https://polygon.io")
        return
    except Exception as e:
        log.error(f"Failed to fetch options data: {e}")
        return

    if not options_data:
        log.warning("No options data returned. Market may be closed.")
        return

    # Get spot price (from first contract's underlying)
    spot_price = options_data[0].get("underlying_asset", {}).get("price", 0)
    if spot_price == 0:
        log.error("Could not determine spot price")
        return

    # Calculate GEX
    gex = calculate_gex(options_data, spot_price)
    regime = classify_regime(gex)

    log.info(f"Results:")
    log.info(f"  {symbol} spot price: ${spot_price:.2f}")
    log.info(f"  Net GEX: {gex:.2f}B")
    log.info(f"  Regime: {regime}")

    if dry_run:
        log.info("[DRY RUN] Skipping webhook trigger")
        return {"gex": gex, "regime": regime, "spot_price": spot_price}

    # Trigger appropriate webhook
    webhook_manager = WebhookManager()

    # Trigger the regime router webhook
    result = await webhook_manager.trigger("gex_regime_router", {
        "regime": regime,
        "gex_value": round(gex, 2),
        "spot_price": round(spot_price, 2),
        "timestamp": now.isoformat(),
    })

    if result["success"]:
        log.info(f"Webhook triggered successfully for regime: {regime}")
    else:
        log.error(f"Webhook trigger failed: {result.get('error')}")

    # Save result for history
    results_dir = Path(__file__).parent.parent / "data"
    results_dir.mkdir(exist_ok=True)
    history_file = results_dir / "gex_history.jsonl"
    with open(history_file, "a") as f:
        f.write(json.dumps({
            "symbol": symbol,
            "gex": round(gex, 2),
            "regime": regime,
            "spot_price": round(spot_price, 2),
            "timestamp": now.isoformat(),
        }) + "\n")

    return {"gex": gex, "regime": regime, "spot_price": spot_price}


def main():
    parser = argparse.ArgumentParser(description="GEX Regime Classification Engine")
    parser.add_argument("--symbol", default="SPY", help="Underlying symbol (default: SPY)")
    parser.add_argument("--dry-run", action="store_true", help="Calculate but don't trigger webhook")
    args = parser.parse_args()

    asyncio.run(run_classification(symbol=args.symbol, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
