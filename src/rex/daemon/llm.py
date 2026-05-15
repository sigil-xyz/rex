import logging
import re
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from rex.config import LlmConfig

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _get_client(config: LlmConfig) -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.api_key or None, base_url=config.base_url)
    return _client


def _build_messages(
    text: str, config: LlmConfig, history: list[ChatCompletionMessageParam]
) -> list[ChatCompletionMessageParam]:
    system: ChatCompletionMessageParam = {"role": "system", "content": config.system_prompt}
    user: ChatCompletionMessageParam = {"role": "user", "content": text}
    return [system, *history, user]


async def respond(text: str, config: LlmConfig, history: list[ChatCompletionMessageParam]) -> str:
    try:
        response = await _get_client(config).chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=_build_messages(text, config, history),
        )
        result = response.choices[0].message.content or ""
        logger.debug("llm response: %s", result[:80])
        return result
    except Exception as e:
        logger.error("llm request failed: %s", e)
        return "Sorry, I couldn't process that."


async def respond_streaming(
    text: str, config: LlmConfig, history: list[ChatCompletionMessageParam]
) -> AsyncGenerator[str, None]:
    try:
        stream = await _get_client(config).chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=_build_messages(text, config, history),
            stream=True,
        )
        buffer = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            buffer += delta
            parts = _SENTENCE_END.split(buffer, maxsplit=1)
            while len(parts) > 1:
                sentence = parts[0].strip()
                if sentence:
                    yield sentence
                buffer = parts[1]
                parts = _SENTENCE_END.split(buffer, maxsplit=1)
        if buffer.strip():
            yield buffer.strip()
    except Exception as e:
        logger.error("llm streaming failed: %s", e)
        yield "Sorry, I couldn't process that."
