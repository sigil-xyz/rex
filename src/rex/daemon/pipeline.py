import asyncio
import json
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Literal

from rex.config import RexConfig
from rex.daemon import llm, tts
from rex.daemon.llm import ToolCallRequest
from rex.daemon.memory import get_history, save_tool_call, save_turn
from rex.daemon.tools import REGISTRY, ToolResult, format_tool_error

logger = logging.getLogger(__name__)

OutputMode = Literal["voice", "text"]

_SPEAK_LIMIT = 300


def _format_tool_result(tool: ToolCallRequest, result: ToolResult) -> str:
    if result.error:
        return f"That didn't work: {format_tool_error(result.error)}"
    text = result.output.strip()
    match tool.name:
        case "write_file":
            return result.output
        case "clipboard_write":
            return "Done, copied to clipboard."
        case "clipboard_read":
            if not text:
                return "The clipboard is empty."
            clipped = text[: _SPEAK_LIMIT - 12]
            return f"Clipboard: {clipped}" + ("…" if len(text) > _SPEAK_LIMIT - 12 else "")
        case "shell":
            if not text or text == "(no output)":
                return "Command finished with no output."
            return text[:_SPEAK_LIMIT] + ("…" if len(text) > _SPEAK_LIMIT else "")
        case "web_search":
            return text[:_SPEAK_LIMIT] + ("…" if len(text) > _SPEAK_LIMIT else "")
        case _:  # read_file and future tools
            if not text:
                return "The file is empty."
            return text[:_SPEAK_LIMIT] + ("…" if len(text) > _SPEAK_LIMIT else "")


def _confirmation_prompt(tool: ToolCallRequest) -> str:
    if tool.name == "shell":
        return f"Run: {tool.args.get('command', '')}?"
    if tool.name == "clipboard_write":
        text = str(tool.args.get("text", ""))[:60]
        return f"Copy to clipboard: {text}?"
    if tool.name == "write_file":
        return f"Write to {tool.args.get('path', 'file')}?"
    return f"Use {tool.name}?"


async def confirm_text(prompt: str) -> bool:
    loop = asyncio.get_running_loop()
    answer: str = await loop.run_in_executor(None, input, f"{prompt} [y/N]: ")
    return answer.strip().lower() in {"y", "yes"}


async def _run_tool_inline(
    tool: ToolCallRequest,
    config: RexConfig,
    db: sqlite3.Connection,
    turn_id: int,
    output_mode: OutputMode,
    on_notify: Callable[[str], Awaitable[None]] | None = None,
) -> None:
    tool_def = REGISTRY.get(tool.name)
    if tool_def is None:
        msg = "I don't know how to do that."
        if output_mode == "text":
            print(msg)
        else:
            await tts.speak(msg, config.tts)
        return

    try:
        result = tool_def.run(tool.args)
    except (KeyError, TypeError) as e:
        logger.error("tool %s called with bad args %r: %s", tool.name, tool.args, e)
        msg = "Something went wrong running that tool."
        if output_mode == "text":
            print(msg)
        else:
            await tts.speak(msg, config.tts)
        return

    result_text = result.output if result.error is None else f"Error: {result.error}"
    logger.info("tool %s result: %s", tool.name, result_text[:120])

    save_tool_call(db, turn_id, tool.name, json.dumps(tool.args), result_text, "completed")

    formatted = _format_tool_result(tool, result)
    save_turn(db, "assistant", formatted)

    if output_mode == "text":
        print(formatted)
    else:
        await tts.speak(formatted, config.tts)
        if on_notify:
            await on_notify(formatted)


async def run_query(
    text: str,
    config: RexConfig,
    db: sqlite3.Connection,
    output_mode: OutputMode,
    on_write_tool: Callable[[ToolCallRequest, int], Awaitable[None]] | None = None,
    on_notify: Callable[[str], Awaitable[None]] | None = None,
) -> None:
    history = get_history(db, config.llm.memory_turns)
    msgs = llm.build_messages(text, config.llm, history)

    sentence_queue: asyncio.Queue[str | None] = asyncio.Queue()
    response_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []

    async def _generate() -> None:
        async for item in llm.respond_streaming_msgs(
            msgs, config.llm, tools_enabled=config.tools.enabled
        ):
            if isinstance(item, ToolCallRequest):
                tool_calls.append(item)
            else:
                await sentence_queue.put(item)
        await sentence_queue.put(None)

    async def _output_loop() -> None:
        while True:
            sentence = await sentence_queue.get()
            if sentence is None:
                break
            response_parts.append(sentence)
            if output_mode == "text":
                print(sentence, end=" ", flush=True)
            else:
                await tts.speak(sentence, config.tts)
        if output_mode == "text" and response_parts:
            print()

    await asyncio.gather(_generate(), _output_loop())

    turn_id = save_turn(db, "user", text)

    if tool_calls:
        tool = tool_calls[0]
        tool_def = REGISTRY.get(tool.name)
        if tool_def and tool_def.trust == "read":
            await _run_tool_inline(tool, config, db, turn_id, output_mode, on_notify)
        else:
            if on_write_tool is not None:
                await on_write_tool(tool, turn_id)
            else:
                prompt = _confirmation_prompt(tool)
                confirmed = await confirm_text(prompt)
                if confirmed:
                    await _run_tool_inline(tool, config, db, turn_id, output_mode, on_notify)
                else:
                    print("Cancelled.")
                    save_tool_call(db, turn_id, tool.name, json.dumps(tool.args), None, "cancelled")
    else:
        response = " ".join(response_parts)
        logger.info("response: %s", response)
        save_turn(db, "assistant", response)
        if on_notify:
            await on_notify(response)
