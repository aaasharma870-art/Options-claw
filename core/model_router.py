"""Cost-aware model routing.

Routes each AI call to the cheapest model that can handle it:
- Haiku ($0.25/MTok): Simple navigation, button identification, yes/no verification
- Sonnet ($3/MTok): Form filling, parameter setting, medium complexity
- Sonnet with extended thinking: Error recovery, novel UI, debugging
"""

from core.config import VERIFIER_MODEL, EXECUTOR_MODEL

# Keywords that indicate simple tasks suitable for Haiku
_SIMPLE_KEYWORDS = frozenset([
    "navigate", "click", "go to", "find", "scroll", "open",
    "which button", "where is", "verify", "confirm", "check",
])

# Keywords that indicate complex tasks requiring Sonnet
_COMPLEX_KEYWORDS = frozenset([
    "configure", "set up", "create", "build", "debug",
    "error", "fix", "recover", "troubleshoot",
])


def route_model(task_description: str, has_error: bool = False,
                retry_count: int = 0) -> str:
    """Pick the cheapest model that can handle this task.

    Args:
        task_description: What the model needs to do.
        has_error: Whether the previous attempt hit an error.
        retry_count: How many times this has been retried.

    Returns:
        Model identifier string.
    """
    # Errors and retries need the smartest model
    if has_error or retry_count > 0:
        return EXECUTOR_MODEL

    desc_lower = task_description.lower()

    # Check if task is simple enough for Haiku
    if any(word in desc_lower for word in _SIMPLE_KEYWORDS):
        has_complex = any(word in desc_lower for word in _COMPLEX_KEYWORDS)
        if not has_complex:
            return VERIFIER_MODEL

    # Default to Sonnet
    return EXECUTOR_MODEL
