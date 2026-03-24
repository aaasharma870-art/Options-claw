"""Verification agent using Claude Haiku.

After any critical action (bot creation, mode change, automation save),
takes ONE screenshot and asks Haiku a specific yes/no question.

Cost: ~$0.003 per verification. Catches the "confident but wrong" failure mode.
"""

import anthropic

from core.config import VERIFIER_MODEL, get_api_key


async def verify_action(screenshot_base64: str, question: str) -> tuple[bool, str]:
    """Ask Haiku to verify a screenshot matches expectations.

    Args:
        screenshot_base64: PNG screenshot encoded as base64 string.
        question: Yes/no question about what should be visible.

    Returns:
        (passed, raw_answer) tuple.
    """
    client = anthropic.Anthropic(api_key=get_api_key())

    response = client.messages.create(
        model=VERIFIER_MODEL,
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64,
                    },
                },
                {
                    "type": "text",
                    "text": f"Answer YES or NO only: {question}",
                },
            ],
        }],
    )

    answer = response.content[0].text.strip().upper()
    return "YES" in answer, answer


async def verify_bot_created(screenshot_base64: str, bot_name: str) -> tuple[bool, str]:
    """Verify a bot was created with the expected name."""
    return await verify_action(
        screenshot_base64,
        f"Does this screenshot show a bot named '{bot_name}'?",
    )


async def verify_paper_mode(screenshot_base64: str) -> tuple[bool, str]:
    """Verify the current bot is in PAPER mode."""
    return await verify_action(
        screenshot_base64,
        "Is this bot set to PAPER trading mode (not live/real)?",
    )


async def verify_automation_saved(screenshot_base64: str,
                                  automation_name: str) -> tuple[bool, str]:
    """Verify an automation was saved successfully."""
    return await verify_action(
        screenshot_base64,
        f"Does this screenshot show an automation named '{automation_name}' was saved?",
    )


async def verify_no_errors(screenshot_base64: str) -> tuple[bool, str]:
    """Check that no error messages are visible."""
    passed, answer = await verify_action(
        screenshot_base64,
        "Is there an error message or warning visible on this screen?",
    )
    # Invert: we want True when there are NO errors
    return not passed, answer
