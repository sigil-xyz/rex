import logging
from collections.abc import Callable
from datetime import datetime

logger = logging.getLogger(__name__)

_responses: dict[str, Callable[[], str]] = {
    "time": lambda: f"It's {datetime.now().strftime('%I:%M %p')}.",
    "day": lambda: f"Today is {datetime.now().strftime('%A, %B %d')}.",
    "hello": lambda: "Hello. How can I help?",
    "help": lambda: "I can tell you the time, date, or just say hello.",
}
_FALLBACK = "I didn't catch that. For now try asking for the time or date."


def respond(text: str) -> str:
    text_lower = text.lower()

    for keyword, responsder in _responses.items():
        if keyword in text_lower:
            logger.debug("match found: %s", keyword)
            return responsder()
    logger.warning("no keyword matched in %r", text)
    return _FALLBACK
