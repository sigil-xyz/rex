import json
import logging
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam

from rex.config import LlmConfig
from rex.daemon.tools import get_tool_schemas

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ToolCallRequest:
    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)


def _get_client(config: LlmConfig) -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.api_key or None, base_url=config.base_url)
    return _client


def build_messages(
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
            messages=build_messages(text, config, history),
        )
        result = response.choices[0].message.content or ""
        logger.debug("llm response: %s", result[:80])
        return result
    except Exception as e:
        logger.error("llm request failed: %s", e)
        return "Sorry, I couldn't process that."


async def respond_streaming_msgs(
    msgs: list[ChatCompletionMessageParam],
    config: LlmConfig,
    tools_enabled: bool = True,
) -> AsyncGenerator[str | ToolCallRequest, None]:
    tools = get_tool_schemas() if tools_enabled else []
    try:
        stream: AsyncStream[ChatCompletionChunk]
        if tools:
            stream = await _get_client(config).chat.completions.create(  # type: ignore[assignment]
                model=config.model,
                max_tokens=config.max_tokens,
                messages=msgs,
                stream=True,
                tools=tools,  # type: ignore[arg-type]
            )
        else:
            stream = await _get_client(config).chat.completions.create(
                model=config.model,
                max_tokens=config.max_tokens,
                messages=msgs,
                stream=True,
            )

        buffer = ""
        tool_call_id = ""
        tool_name = ""
        args_buffer = ""
        in_tool_call = False

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.tool_calls:
                in_tool_call = True
                tc = delta.tool_calls[0]
                # Only accumulate the first tool call (index 0).
                # When the model returns multiple parallel calls, skip the rest.
                if getattr(tc, "index", 0) != 0:
                    continue
                if tc.id:
                    tool_call_id = tc.id
                if tc.function:
                    # Some providers (e.g. aicredits.in) repeat the full name in every chunk.
                    # Only capture it once — the first non-empty value wins.
                    if tc.function.name and not tool_name:
                        tool_name = tc.function.name
                    if tc.function.arguments:
                        args_buffer += tc.function.arguments
            elif delta.content:
                buffer += delta.content
                parts = _SENTENCE_END.split(buffer, maxsplit=1)
                while len(parts) > 1:
                    sentence = parts[0].strip()
                    if sentence:
                        yield sentence
                    buffer = parts[1]
                    parts = _SENTENCE_END.split(buffer, maxsplit=1)

        if in_tool_call and tool_name:
            try:
                args = json.loads(args_buffer) if args_buffer else {}
            except json.JSONDecodeError:
                logger.warning("tool call args not valid JSON: %r", args_buffer)
                args = {}
            yield ToolCallRequest(id=tool_call_id, name=tool_name, args=args)
        elif buffer.strip():
            yield buffer.strip()

    except Exception as e:
        logger.error("llm streaming failed: %s", e)
        yield "Sorry, I couldn't process that."


async def respond_streaming(
    text: str, config: LlmConfig, history: list[ChatCompletionMessageParam]
) -> AsyncGenerator[str | ToolCallRequest, None]:
    msgs = build_messages(text, config, history)
    async for item in respond_streaming_msgs(msgs, config):
        yield item


async def respond_with_tool_result(
    messages: list[ChatCompletionMessageParam],
    tool_call: ToolCallRequest,
    result: str,
    config: LlmConfig,
) -> AsyncGenerator[str, None]:
    """Stream a follow-up LLM response after a tool call.

    Not called by the current pipeline — results are formatted locally in main.py
    to avoid a second API round-trip. Reserved for use when richer LLM-generated
    summaries of tool output are needed (planned for v0.4).
    """
    assistant_msg: ChatCompletionMessageParam = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.args),
                },
            }
        ],
    }
    tool_msg: ChatCompletionMessageParam = {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result,
    }
    extended = [*messages, assistant_msg, tool_msg]

    try:
        stream = await _get_client(config).chat.completions.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=extended,
            stream=True,
        )
        buffer = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            buffer += content
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
        logger.error("llm tool result streaming failed: %s", e)
        yield "Sorry, I couldn't process that."
