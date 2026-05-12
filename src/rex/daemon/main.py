import asyncio
import logging
import os
import signal
from pathlib import Path

import numpy as np

from rex.config import NotificationConfig, RexConfig, load_config
from rex.daemon import llm, tts
from rex.daemon.audio import AudioRecorder
from rex.daemon.stt import Transcriber

logger = logging.getLogger(__name__)


def get_socket_path() -> Path:
    runtime_user_directory = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_user_directory) / "rex.sock"


async def _notify(text: str, config: NotificationConfig) -> None:
    if not config.enabled:
        return

    await asyncio.create_subprocess_exec(
        "notify-send",
        "--expire-time",
        str(config.timeout),
        "rex",
        text,
        stderr=asyncio.subprocess.DEVNULL,
    )


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
        self._server: asyncio.Server | None = None
        self._socket_path: Path | None = None

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

    async def _on_start(self) -> None:
        if self._recording:
            logger.warning("already recording — ignoring start")
            return
        self._recording = True
        self._recorder.start()
        logger.info("recording started")

    async def _on_stop(self) -> None:
        if not self._recording:
            logger.warning("not recording — ignoring stop")
            return
        self._recording = False

        audio: np.ndarray = self._recorder.stop()

        loop = asyncio.get_running_loop()
        text: str = await loop.run_in_executor(
            None,  # default ThreadPoolExecutor
            self._transcriber.transcribe,
            audio,
        )
        logger.info("transcribed: %s", text)

        response: str = llm.respond(text)
        logger.info("response: %s", response)

        await asyncio.gather(
            tts.speak(response, self._config.tts),
            _notify(response, self._config.notification),
        )

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
