"""Playwright action: Add an automation to an existing bot."""

import logging

log = logging.getLogger("options-claw.actions.create_automation")


async def create_automation(runner, subtask: dict) -> tuple[bool, str]:
    """Add an automation to an existing OA bot.

    Expected subtask keys:
        automation_name: str — Name for the automation
        bot_url: str — URL path to the bot (e.g., "/bots/12345")
        trigger_type: str — Trigger type (e.g., "interval", "webhook")
        interval_minutes: int — Interval in minutes (for interval triggers)
    """
    name = subtask.get("automation_name", subtask.get("title", "New Automation"))
    bot_url = subtask.get("bot_url", "")
    trigger_type = subtask.get("trigger_type", "interval")

    try:
        # Navigate to bot's automations tab
        if bot_url:
            await runner.navigate_to(bot_url)
        await runner.click("bot_config", "automations_tab")
        log.info("Navigated to Automations tab")

        # Click Add Automation
        await runner.click("bot_config", "add_automation_button")
        log.info("Clicked Add Automation")

        # Fill automation name
        await runner.fill("bot_config", "automation_name_input", name)
        log.info(f"Set automation name: {name}")

        # Set trigger
        if trigger_type == "interval":
            interval = subtask.get("interval_minutes", 30)
            await runner.fill("bot_config", "interval_input", str(interval))
            log.info(f"Set interval: {interval} minutes")

        # Save
        await runner.click("bot_config", "save_automation_button")
        log.info("Saved automation")

        await runner.page.wait_for_load_state("networkidle")

        return True, f"Automation '{name}' created"

    except Exception as e:
        log.error(f"Failed to create automation: {e}")
        raise
