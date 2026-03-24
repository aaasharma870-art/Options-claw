"""Playwright action: Configure an existing automation's parameters."""

import logging

log = logging.getLogger("options-claw.actions.configure_automation")


async def configure_automation(runner, subtask: dict) -> tuple[bool, str]:
    """Set parameters on an existing OA automation.

    Expected subtask keys:
        automation_name: str — Name of the automation to configure
        bot_url: str — URL path to the bot
        parameters: dict — Key-value pairs to set
    """
    name = subtask.get("automation_name", subtask.get("title", ""))
    bot_url = subtask.get("bot_url", "")
    parameters = subtask.get("parameters", {})

    try:
        if bot_url:
            await runner.navigate_to(bot_url)
        await runner.click("bot_config", "automations_tab")

        # Click on the specific automation (by text match)
        automation_selector = f"text='{name}'"
        await runner.page.click(automation_selector, timeout=10000)
        log.info(f"Opened automation: {name}")

        # Apply each parameter
        for key, value in parameters.items():
            try:
                selector = runner.get_selector("bot_config", key)
                if isinstance(value, bool):
                    if value:
                        await runner.page.check(selector)
                    else:
                        await runner.page.uncheck(selector)
                else:
                    await runner.page.fill(selector, str(value))
                log.info(f"Set {key} = {value}")
            except Exception as e:
                log.warning(f"Could not set {key}: {e}")

        # Save
        await runner.click("bot_config", "save_automation_button")
        await runner.page.wait_for_load_state("networkidle")

        return True, f"Automation '{name}' configured with {len(parameters)} parameters"

    except Exception as e:
        log.error(f"Failed to configure automation: {e}")
        raise
