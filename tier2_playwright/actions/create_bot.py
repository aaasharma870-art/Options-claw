"""Playwright action: Create a new bot in Option Alpha."""

import logging

log = logging.getLogger("options-claw.actions.create_bot")


async def create_bot(runner, subtask: dict) -> tuple[bool, str]:
    """Create a new OA bot with the given parameters.

    Expected subtask keys:
        bot_name: str — Name for the new bot
        symbol: str — Underlying symbol (e.g., "SPY")
        strategy_type: str — Strategy type (e.g., "Credit Spreads")
        mode: str — "paper" or "live"
    """
    bot_name = subtask.get("bot_name", subtask.get("title", "New Bot"))
    symbol = subtask.get("symbol", "SPY")
    mode = subtask.get("mode", "paper").lower()

    try:
        # Navigate to bots page
        await runner.navigate_to("/bots")
        log.info("Navigated to Bots page")

        # Click New Bot
        await runner.click("dashboard", "new_bot_button")
        log.info("Clicked New Bot")

        # Fill bot name
        await runner.fill("bot_creation", "bot_name_input", bot_name)
        log.info(f"Set bot name: {bot_name}")

        # Fill symbol
        await runner.fill("bot_creation", "symbol_input", symbol)
        log.info(f"Set symbol: {symbol}")

        # Select paper mode
        if mode == "paper":
            await runner.click("bot_creation", "paper_mode_toggle")
            log.info("Selected PAPER mode")

        # Click Create
        await runner.click("bot_creation", "create_button")
        log.info("Clicked Create")

        # Wait for confirmation
        await runner.page.wait_for_load_state("networkidle")

        # Take verification screenshot
        screenshot = await runner.screenshot_base64()

        return True, f"Bot '{bot_name}' created for {symbol} in {mode} mode"

    except Exception as e:
        log.error(f"Failed to create bot: {e}")
        raise  # Let the orchestrator handle fallback to Tier 3
