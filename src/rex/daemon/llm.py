import logging

from openai import OpenAI

from rex.config import LlmConfig

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def respond(text: str, config: LlmConfig) -> str:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.api_key or None, base_url=config.base_url)
    try:
        response = _client.chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=[
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": text},
            ],
        )
        result = response.choices[0].message.content or ""
        logger.debug("llm response: %s", result[:80])
        return result
    except Exception as e:
        logger.error("llm request failed: %s", e)
        return "Sorry, I couldn't process that."
