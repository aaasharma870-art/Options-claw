"""Playwright action: Check bot status and P&L from OA dashboard."""

import logging

log = logging.getLogger("options-claw.actions.check_bot_status")


async def check_bot_status(runner, subtask: dict) -> tuple[bool, str]:
    """Scrape bot dashboard for status, mode, and P&L.

    Expected subtask keys:
        bot_url: str — URL path to the bot (e.g., "/bots/12345")
        bot_name: str — Name of the bot to find on dashboard
    """
    bot_url = subtask.get("bot_url", "")
    bot_name = subtask.get("bot_name", "")

    try:
        if bot_url:
            await runner.navigate_to(bot_url)
        else:
            await runner.navigate_to("/bots")
            if bot_name:
                await runner.page.click(f"text='{bot_name}'", timeout=10000)

        await runner.page.wait_for_load_state("networkidle")

        # Scrape status info
        status_info = {}

        try:
            status_el = await runner.page.query_selector(
                runner.get_selector("bot_dashboard", "bot_status")
            )
            if status_el:
                status_info["status"] = await status_el.inner_text()
        except Exception:
            pass

        try:
            mode_el = await runner.page.query_selector(
                runner.get_selector("bot_dashboard", "bot_mode")
            )
            if mode_el:
                status_info["mode"] = await mode_el.inner_text()
        except Exception:
            pass

        try:
            pnl_el = await runner.page.query_selector(
                runner.get_selector("bot_dashboard", "bot_pnl")
            )
            if pnl_el:
                status_info["pnl"] = await pnl_el.inner_text()
        except Exception:
            pass

        summary = ", ".join(f"{k}: {v}" for k, v in status_info.items())
        if not summary:
            summary = "Status scraped but no fields found (selectors may need updating)"

        log.info(f"Bot status: {summary}")
        return True, summary

    except Exception as e:
        log.error(f"Failed to check bot status: {e}")
        raise
