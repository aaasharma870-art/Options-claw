"""Webhook manager for Option Alpha.

OA supports inbound webhooks — external scripts can trigger automations
via HTTP POST. This replaces the most expensive part (recurring
screen-clicking) with a free HTTP call.

Flow:
    Python calculates GEX -> classifies regime -> POST to OA webhook
    No Docker, no browser, no AI.
"""

import json
import logging
from pathlib import Path

import httpx

from core.config import WEBHOOK_CONFIG_PATH

log = logging.getLogger("options-claw.webhooks")


class WebhookManager:
    """Manages OA webhook URLs and sends trigger requests."""

    def __init__(self, config_path: Path = WEBHOOK_CONFIG_PATH):
        self.config_path = config_path
        self._webhooks: dict[str, dict] = {}
        self._load_config()

    def _load_config(self):
        """Load webhook URLs from config file."""
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text())
            self._webhooks = data.get("webhooks", {})
            log.info(f"Loaded {len(self._webhooks)} webhook(s) from config")
        else:
            log.warning(f"Webhook config not found: {self.config_path}")

    def has_webhook(self, automation_name: str) -> bool:
        """Check if a webhook URL exists for this automation."""
        return automation_name in self._webhooks

    def get_webhook_url(self, automation_name: str) -> str | None:
        """Get the webhook URL for an automation."""
        hook = self._webhooks.get(automation_name)
        if hook:
            return hook.get("url")
        return None

    async def trigger(self, automation_name: str,
                      payload: dict = None) -> dict:
        """Trigger an OA automation via webhook.

        Args:
            automation_name: Name matching a key in webhook_config.json.
            payload: Optional JSON payload to send.

        Returns:
            Dict with "success" bool and optional "error" or "response".
        """
        url = self.get_webhook_url(automation_name)
        if not url:
            return {"success": False, "error": f"No webhook URL for '{automation_name}'"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload or {},
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in (200, 201, 202, 204):
                    log.info(f"Webhook triggered: {automation_name} ({response.status_code})")
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response.text[:500],
                    }
                else:
                    log.warning(f"Webhook failed: {automation_name} ({response.status_code})")
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text[:500],
                    }

        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_webhooks(self) -> dict[str, str]:
        """List all registered webhook names and URLs."""
        return {name: hook.get("url", "") for name, hook in self._webhooks.items()}

    def add_webhook(self, automation_name: str, url: str, description: str = ""):
        """Register a new webhook URL."""
        self._webhooks[automation_name] = {
            "url": url,
            "description": description,
        }
        self._save_config()

    def _save_config(self):
        """Persist webhook config to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"webhooks": self._webhooks}
        self.config_path.write_text(json.dumps(data, indent=2))
