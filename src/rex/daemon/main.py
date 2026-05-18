import asyncio
import json
import logging
import os
import platform
import signal
from pathlib import Path

from rex.config import NotificationConfig, RexConfig, load_config, resolve_socket_path
from rex.daemon import tts
from rex.daemon.audio import SpeechSession
from rex.daemon.llm import ToolCallRequest
from rex.daemon.memory import DEFAULT_DB_PATH, init_db, save_tool_call, save_turn
from rex.daemon.pipeline import _format_tool_result, run_query
from rex.daemon.stt import Transcriber
from rex.daemon.tools import REGISTRY

logger = logging.getLogger(__name__)

_CONFIRM_WORDS = {"yes", "confirm", "do it", "yeah", "yep", "sure", "ok", "okay"}
_MIN_WORDS = 3


def get_socket_path() -> Path:
    return resolve_socket_path()


def _is_valid_transcription(text: str) -> bool:
    return len(text.split()) >= _MIN_WORDS


async def _notify(text: str, config: NotificationConfig) -> None:
    if not config.enabled:
        return

    if platform.system() == "Darwin":
        script = f'display notification "{text}" with title "Rex"'
        proc = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stderr=asyncio.subprocess.DEVNULL,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            "notify-send",
            "--expire-time",
            str(config.timeout),
            "rex",
            text,
            stderr=asyncio.subprocess.DEVNULL,
        )

    await proc.communicate()


def _confirmation_prompt(tool: ToolCallRequest) -> str:
    if tool.name == "shell":
        return f"Run: {tool.args.get('command', '')}?"
    if tool.name == "clipboard_write":
        text = str(tool.args.get("text", ""))[:60]
        return f"Copy to clipboard: {text}?"
    if tool.name == "write_file":
        return f"Write to {tool.args.get('path', 'file')}?"
    return f"Use {tool.name}?"


class RexDaemon:
    def __init__(self, config: RexConfig, transcriber: Transcriber) -> None:
        self._config = config
        self._transcriber = transcriber
        self._session: SpeechSession | None = None
        self._session_task: asyncio.Task[None] | None = None
        self._server: asyncio.Server | None = None
        self._socket_path: Path | None = None
        db_path = config.memory_db or DEFAULT_DB_PATH
        self._db = init_db(db_path)

        # tool confirmation state
        self._pending_tool: ToolCallRequest | None = None
        self._pending_turn_id: int = 0
        self._confirmation_task: asyncio.Task[None] | None = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.readline()
            command = data.decode().strip()
            logger.debug("received: %s", command)
            await self._dispatch(command)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, command: str) -> None:
        match command:
            case "toggle" | "start":
                await self._on_toggle()
            case "stop":
                if self._session is not None:
                    self._session.request_stop()
            case _:
                logger.warning("unknown command: %r", command)

    async def _on_toggle(self) -> None:
        if self._session_task is not None:
            if self._session is not None:
                self._session.request_stop()
            logger.info("session stop requested via toggle")
            return

        if self._confirmation_task is not None:
            self._confirmation_task.cancel()
            self._confirmation_task = None

        self._session_task = asyncio.create_task(self._run_session())
        logger.info("session armed")

    async def _run_session(self) -> None:
        session = SpeechSession(self._config.audio, self._config.vad)
        self._session = session
        try:
            audio = await session.run()
        finally:
            self._session = None
            self._session_task = None

        if audio is None or len(audio) == 0:
            logger.info("no audio captured — discarding")
            return

        loop = asyncio.get_running_loop()
        text: str = await loop.run_in_executor(None, self._transcriber.transcribe, audio)
        logger.info("transcribed: %r", text)

        if not _is_valid_transcription(text):
            logger.info("confidence gate — discarding %r", text)
            return

        if self._pending_tool is not None:
            await self._on_confirmation(text)
        else:
            await self._on_query(text)

    async def _on_query(self, text: str) -> None:
        async def _on_notify(response: str) -> None:
            await _notify(response, self._config.notification)

        await run_query(
            text,
            self._config,
            self._db,
            output_mode="voice",
            on_write_tool=self._ask_confirmation,
            on_notify=_on_notify,
        )

    async def _run_tool(self, tool: ToolCallRequest, turn_id: int) -> None:
        tool_def = REGISTRY.get(tool.name)
        if tool_def is None:
            await tts.speak("I don't know how to do that.", self._config.tts)
            return

        try:
            result = tool_def.run(tool.args)
        except (KeyError, TypeError) as e:
            logger.error("tool %s called with bad args %r: %s", tool.name, tool.args, e)
            await tts.speak("Something went wrong running that tool.", self._config.tts)
            return
        result_text = result.output if result.error is None else f"Error: {result.error}"
        logger.info("tool %s result: %s", tool.name, result_text[:120])

        save_tool_call(
            self._db, turn_id, tool.name, json.dumps(tool.args), result_text, "completed"
        )

        spoken = _format_tool_result(tool, result)
        save_turn(self._db, "assistant", spoken)
        await tts.speak(spoken, self._config.tts)
        await _notify(spoken, self._config.notification)

    async def _ask_confirmation(self, tool: ToolCallRequest, turn_id: int) -> None:
        self._pending_tool = tool
        self._pending_turn_id = turn_id

        prompt = _confirmation_prompt(tool)
        logger.info("asking confirmation: %s", prompt)
        await tts.speak(prompt, self._config.tts)

        self._confirmation_task = asyncio.create_task(self._confirmation_timeout())

    async def _confirmation_timeout(self) -> None:
        await asyncio.sleep(self._config.tools.confirmation_timeout)
        if self._pending_tool is not None:
            tool = self._pending_tool
            turn_id = self._pending_turn_id
            self._pending_tool = None
            self._pending_turn_id = 0
            self._confirmation_task = None
            logger.info("confirmation timeout — cancelling %s", tool.name)
            save_tool_call(self._db, turn_id, tool.name, json.dumps(tool.args), None, "timeout")
            await tts.speak("Cancelled.", self._config.tts)

    async def _on_confirmation(self, text: str) -> None:
        if self._confirmation_task is not None:
            self._confirmation_task.cancel()
            self._confirmation_task = None

        tool = self._pending_tool
        turn_id = self._pending_turn_id
        self._pending_tool = None
        self._pending_turn_id = 0

        assert tool is not None

        text_lower = text.lower()
        confirmed = any(w in text_lower for w in _CONFIRM_WORDS)

        if confirmed:
            logger.info("confirmed — running %s", tool.name)
            await self._run_tool(tool, turn_id)
        else:
            logger.info("cancelled by user — %s", tool.name)
            save_tool_call(self._db, turn_id, tool.name, json.dumps(tool.args), None, "cancelled")
            await tts.speak("Cancelled.", self._config.tts)

    async def serve(self, socket_path: Path) -> None:
        if socket_path.exists():
            socket_path.unlink()

        self._server = await asyncio.start_unix_server(self._handle_client, path=str(socket_path))
        os.chmod(socket_path, 0o600)
        self._socket_path = socket_path
        logger.info("rex is listening on %s", socket_path)

        async with self._server:
            await self._server.serve_forever()

    async def shutdown(self) -> None:
        if self._session is not None:
            self._session.request_stop()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        if self._socket_path is not None:
            self._socket_path.unlink(missing_ok=True)
            logger.info("removed socket %s", self._socket_path)


async def _main() -> None:
    config = load_config()

    transcriber = Transcriber(config.stt)
    transcriber.load()  # blocks briefly — loads whisper model from disk

    daemon = RexDaemon(config, transcriber)
    socket_path = resolve_socket_path(config.daemon.socket_path)

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(daemon.shutdown()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(daemon.shutdown()))

    if platform.system() == "Linux":
        proc = await asyncio.create_subprocess_exec(
            "pactl",
            "suspend-sink",
            "@DEFAULT_SINK@",
            "0",
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()

    await daemon.serve(socket_path)


def run() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("httpcore", "httpx", "hpack", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    asyncio.run(_main())
