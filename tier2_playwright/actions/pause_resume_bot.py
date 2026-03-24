"""Playwright action: Pause or resume a bot."""

import logging

log = logging.getLogger("options-claw.actions.pause_resume")


async def toggle_bot(runner, subtask: dict) -> tuple[bool, str]:
    """Toggle a bot between active and paused state.

    Expected subtask keys:
        bot_url: str — URL path to the bot
        bot_name: str — Name of the bot
        type: str — "pause_bot" or "resume_bot"
    """
    bot_url = subtask.get("bot_url", "")
    bot_name = subtask.get("bot_name", "")
    action = subtask.get("type", "pause_bot")

    try:
        if bot_url:
            await runner.navigate_to(bot_url)
        else:
            await runner.navigate_to("/bots")
            if bot_name:
                await runner.page.click(f"text='{bot_name}'", timeout=10000)

        await runner.page.wait_for_load_state("networkidle")

        if action == "pause_bot":
            await runner.click("bot_dashboard", "pause_button")
            log.info(f"Paused bot: {bot_name}")
        else:
            await runner.click("bot_dashboard", "resume_button")
            log.info(f"Resumed bot: {bot_name}")

        # Confirm modal if present
        try:
            await runner.click("common", "confirm_modal_yes")
        except Exception:
            pass  # No confirmation modal

        await runner.page.wait_for_load_state("networkidle")

        verb = "Paused" if action == "pause_bot" else "Resumed"
        return True, f"{verb} bot: {bot_name or 'current'}"

    except Exception as e:
        log.error(f"Failed to {action}: {e}")
        raise
