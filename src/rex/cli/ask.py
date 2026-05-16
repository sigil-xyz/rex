import asyncio
import sqlite3
import sys
from pathlib import Path

from rex.config import RexConfig, load_config, resolve_output_mode
from rex.daemon.memory import DEFAULT_DB_PATH, init_db
from rex.daemon.pipeline import run_query


def _setup() -> tuple[RexConfig, sqlite3.Connection, str]:
    config = load_config()
    if not config.llm.api_key:
        print(
            "Error: llm.api_key is not set in ~/.config/rex/config.toml",
            file=sys.stderr,
        )
        sys.exit(1)
    output_mode = resolve_output_mode(config.output.mode, input_was_voice=False)
    db_path = config.memory_db or DEFAULT_DB_PATH
    db = init_db(db_path)
    return config, db, output_mode


def ask_main() -> None:
    args = sys.argv[1:]
    if not args:
        print("usage: rex-ask <question>", file=sys.stderr)
        sys.exit(1)
    question = " ".join(args)
    config, db, output_mode = _setup()
    asyncio.run(_ask(question, config, db, output_mode))


async def _ask(
    text: str,
    config: RexConfig,
    db: sqlite3.Connection,
    output_mode: str,
) -> None:
    await run_query(text, config, db, output_mode, cwd=Path.cwd())  # type: ignore[arg-type]


def chat_main() -> None:
    config, db, output_mode = _setup()
    asyncio.run(_chat(config, db, output_mode))


async def _chat(
    config: RexConfig,
    db: sqlite3.Connection,
    output_mode: str,
) -> None:
    loop = asyncio.get_running_loop()
    print("Rex  (type 'exit' to quit)\n")
    try:
        while True:
            try:
                line: str = await loop.run_in_executor(None, input, "You: ")
            except EOFError:
                break
            line = line.strip()
            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                break
            await run_query(line, config, db, output_mode, cwd=Path.cwd())  # type: ignore[arg-type]
    except KeyboardInterrupt:
        print()
