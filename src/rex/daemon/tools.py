import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ToolTrust = Literal["read", "write", "execute"]

_HOME = Path.home()
_TRUNCATE_AT = 4000

_SHELL_BLOCKLIST = [
    "rm -rf",
    "sudo",
    " dd ",
    "dd if",
    "mkfs",
    ":(){ :|:& };:",
]


@dataclass
class ToolResult:
    output: str
    error: str | None = None


@dataclass
class ToolDef:
    name: str
    description: str
    trust: ToolTrust
    parameters: dict[str, Any]
    run: Callable[[dict[str, Any]], ToolResult]


REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    REGISTRY[tool.name] = tool


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in REGISTRY.values()
    ]


def _truncate(text: str) -> str:
    if len(text) <= _TRUNCATE_AT:
        return text
    return text[:_TRUNCATE_AT] + f"\n[truncated — {len(text) - _TRUNCATE_AT} chars omitted]"


# --- tool implementations ---


def _read_file(args: dict[str, Any]) -> ToolResult:
    path = Path(args["path"]).expanduser().resolve()
    try:
        path.relative_to(_HOME)
    except ValueError:
        return ToolResult(output="", error="Access denied: path is outside home directory")
    try:
        content = path.read_text(errors="replace")
        return ToolResult(output=_truncate(content))
    except FileNotFoundError:
        return ToolResult(output="", error=f"File not found: {path}")
    except IsADirectoryError:
        return ToolResult(output="", error=f"Path is a directory: {path}")
    except OSError as e:
        return ToolResult(output="", error=str(e))


def _clipboard_read(_: dict[str, Any]) -> ToolResult:
    try:
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ToolResult(output="", error=result.stderr.strip() or "wl-paste failed")
        return ToolResult(output=_truncate(result.stdout))
    except FileNotFoundError:
        return ToolResult(output="", error="wl-paste not found — install wl-clipboard")
    except subprocess.TimeoutExpired:
        return ToolResult(output="", error="clipboard read timed out")


def _clipboard_write(args: dict[str, Any]) -> ToolResult:
    text: str = args["text"]
    try:
        result = subprocess.run(
            ["wl-copy"],
            input=text,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ToolResult(output="", error=result.stderr.strip() or "wl-copy failed")
        return ToolResult(output="Copied to clipboard.")
    except FileNotFoundError:
        return ToolResult(output="", error="wl-copy not found — install wl-clipboard")
    except subprocess.TimeoutExpired:
        return ToolResult(output="", error="clipboard write timed out")


def _shell(args: dict[str, Any]) -> ToolResult:
    command: str = args["command"]
    for blocked in _SHELL_BLOCKLIST:
        if blocked in command:
            return ToolResult(output="", error=f"Command rejected: contains blocked pattern '{blocked}'")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = result.stdout + result.stderr
        return ToolResult(output=_truncate(combined) if combined else "(no output)")
    except subprocess.TimeoutExpired:
        return ToolResult(output="", error="Command timed out after 30s")
    except OSError as e:
        return ToolResult(output="", error=str(e))


def _write_file(args: dict[str, Any]) -> ToolResult:
    path = Path(args["path"]).expanduser().resolve()
    try:
        path.relative_to(_HOME)
    except ValueError:
        return ToolResult(output="", error="Access denied: path is outside home directory")
    content: str = args["content"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return ToolResult(output=f"Written {len(content)} characters to {path}")
    except OSError as e:
        return ToolResult(output="", error=str(e))


def _web_search(args: dict[str, Any]) -> ToolResult:
    query: str = args["query"]
    try:
        result = subprocess.run(
            ["ddgr", "--noua", "--json", "-n", "5", query],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return ToolResult(output="", error=result.stderr.strip() or "ddgr failed")
        try:
            items: list[dict[str, Any]] = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ToolResult(output="", error="ddgr returned invalid JSON")
        if not items:
            return ToolResult(output="No results found.")
        lines = []
        for i, item in enumerate(items, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            abstract = item.get("abstract", "")
            lines.append(f"{i}. {title}\n   {url}\n   {abstract}")
        return ToolResult(output="\n\n".join(lines))
    except FileNotFoundError:
        return ToolResult(output="", error="ddgr not found — install ddgr")
    except subprocess.TimeoutExpired:
        return ToolResult(output="", error="web search timed out after 15s")


# --- registration ---

register(ToolDef(
    name="read_file",
    description="Read the contents of a file on the user's machine. Only files within the home directory are accessible.",
    trust="read",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or ~ path to the file"},
        },
        "required": ["path"],
    },
    run=_read_file,
))

register(ToolDef(
    name="write_file",
    description="Write text content to a file on the user's machine. Creates the file and any parent directories if they don't exist. Only paths within the home directory are allowed.",
    trust="write",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or ~ path to the file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        "required": ["path", "content"],
    },
    run=_write_file,
))

register(ToolDef(
    name="clipboard_read",
    description="Read the current text content of the Wayland clipboard.",
    trust="read",
    parameters={"type": "object", "properties": {}, "required": []},
    run=_clipboard_read,
))

register(ToolDef(
    name="clipboard_write",
    description="Write text to the Wayland clipboard.",
    trust="write",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to copy to clipboard"},
        },
        "required": ["text"],
    },
    run=_clipboard_write,
))

register(ToolDef(
    name="shell",
    description="Run a shell command and return its output. Dangerous commands are blocked.",
    trust="execute",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
        },
        "required": ["command"],
    },
    run=_shell,
))

register(ToolDef(
    name="web_search",
    description="Search the web via DuckDuckGo and return the top 5 results.",
    trust="read",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    },
    run=_web_search,
))
