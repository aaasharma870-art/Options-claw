"""Central configuration for Options-Claw v3."""

import os
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_DIR = PROJECT_ROOT / "tasks"
RESULTS_DIR = Path("/tmp/options_claw_results")
TODO_FILE = Path("/tmp/options_claw_todo.md")
LOG_FILE = Path("/tmp/options_claw_execution.log")
LEARNING_DB_PATH = DATA_DIR / "learning.db"
SESSION_COOKIES_PATH = DATA_DIR / "session_cookies.json"
SELECTOR_FILE = PROJECT_ROOT / "tier2_playwright" / "ui_selectors.json"
WEBHOOK_CONFIG_PATH = PROJECT_ROOT / "tier1_webhooks" / "webhook_config.json"

# ============================================================
# MODELS
# ============================================================

PLANNER_MODEL = "claude-sonnet-4-5-20250929"
EXECUTOR_MODEL = "claude-sonnet-4-5-20250929"
VERIFIER_MODEL = "claude-haiku-4-5-20251001"

# ============================================================
# EXECUTION LIMITS
# ============================================================

MAX_SCREENSHOTS_IN_CONTEXT = 3
MAX_SUBTASK_RETRIES = 2
SPECULATIVE_VERIFICATION_INTERVAL = 5  # Verify every N actions
SELECTOR_CONFIDENCE_THRESHOLD = 0.8    # Min confidence to use Playwright tier
PARALLEL_MAX_WORKERS = 4               # Max simultaneous Playwright contexts

# ============================================================
# COST ESTIMATES (per 1M tokens)
# ============================================================

COST_PER_M_INPUT = {
    "claude-sonnet-4-5-20250929": 3.00,
    "claude-haiku-4-5-20251001": 0.25,
}
COST_PER_M_OUTPUT = {
    "claude-sonnet-4-5-20250929": 15.00,
    "claude-haiku-4-5-20251001": 1.25,
}
COST_PER_M_CACHED_INPUT = {
    "claude-sonnet-4-5-20250929": 0.30,
    "claude-haiku-4-5-20251001": 0.025,
}

# ============================================================
# OA (Option Alpha) SETTINGS
# ============================================================

OA_BASE_URL = "https://app.optionalpha.com"
OA_BOTS_URL = f"{OA_BASE_URL}/bots"
OA_LOGIN_URL = f"{OA_BASE_URL}/login"

# ============================================================
# API KEY (loaded from environment or .env)
# ============================================================


def get_api_key() -> str:
    """Load Anthropic API key from environment or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()

    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Set it in environment or create .env from .env.template"
    )
