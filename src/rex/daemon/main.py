import asyncio
import logging
import os
import platform
import signal
from pathlib import Path

import numpy as np

from rex.config import NotificationConfig, RexConfig, load_config
from rex.daemon import llm, tts
from rex.daemon.audio import AudioRecorder
from rex.daemon.memory import DEFAULT_DB_PATH, get_history, init_db, save_turn
from rex.daemon.stt import Transcriber

logger = logging.getLogger(__name__)


def get_socket_path() -> Path:
    runtime_user_directory = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_user_directory) / "rex.sock"


async def _notify(text: str, config: NotificationConfig) -> None:
    if not config.enabled:
        return

    if platform.system() == "Darwin":
        # macOS: osascript is always available, no extra deps
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


class RexDaemon:
    def __init__(
        self,
        config: RexConfig,
        recorder: AudioRecorder,
        transcriber: Transcriber,
    ) -> None:
        self._config = config
        self._recorder = recorder
        self._transcriber = transcriber
        self._recording: bool = False
        self._timeout_task: asyncio.Task[None] | None = None
        self._server: asyncio.Server | None = None
        self._socket_path: Path | None = None
        db_path = config.memory_db or DEFAULT_DB_PATH
        self._db = init_db(db_path)

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
            case "start":
                await self._on_start()
            case "stop":
                await self._on_stop()
            case _:
                logger.warning("unknown command: %r", command)

    async def _recording_timeout(self) -> None:
        timeout = self._config.daemon.recording_timeout
        await asyncio.sleep(timeout)
        logger.warning("recording timeout (%ds) — forcing stop", timeout)
        await self._on_stop()

    async def _on_start(self) -> None:
        if self._recording:
            logger.warning("already recording — ignoring start")
            return
        self._recording = True
        self._recorder.start()
        self._timeout_task = asyncio.create_task(self._recording_timeout())
        logger.info("recording started")

    async def _on_stop(self) -> None:
        if not self._recording:
            logger.warning("not recording — ignoring stop")
            return
        self._recording = False
        if self._timeout_task is not None:
            self._timeout_task.cancel()
            self._timeout_task = None

        audio: np.ndarray = self._recorder.stop()

        loop = asyncio.get_running_loop()
        text: str = await loop.run_in_executor(
            None,  # default ThreadPoolExecutor
            self._transcriber.transcribe,
            audio,
        )
        logger.info("transcribed: %s", text)

        history = get_history(self._db, self._config.llm.memory_turns)
        sentence_queue: asyncio.Queue[str | None] = asyncio.Queue()
        response_parts: list[str] = []

        async def _generate() -> None:
            async for sentence in llm.respond_streaming(text, self._config.llm, history):
                await sentence_queue.put(sentence)
            await sentence_queue.put(None)

        async def _speak_loop() -> None:
            while True:
                sentence = await sentence_queue.get()
                if sentence is None:
                    break
                response_parts.append(sentence)
                await tts.speak(sentence, self._config.tts)

        await asyncio.gather(_generate(), _speak_loop())

        response = " ".join(response_parts)
        logger.info("response: %s", response)
        save_turn(self._db, "user", text)
        save_turn(self._db, "assistant", response)
        await _notify(response, self._config.notification)

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
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        if self._socket_path is not None:
            self._socket_path.unlink(missing_ok=True)
            logger.info("removed socket %s", self._socket_path)


async def _main() -> None:
    config = load_config()

    recorder = AudioRecorder(config.audio)
    transcriber = Transcriber(config.stt)
    transcriber.load()  # blocks briefly — loads whisper model from disk

    daemon = RexDaemon(config, recorder, transcriber)
    socket_path = get_socket_path()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(daemon.shutdown()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(daemon.shutdown()))

    # Prevent PipeWire from suspending the audio sink — avoids Bluetooth A2DP
    # re-connection delay that clips the start of TTS responses (Linux/PipeWire only)
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
