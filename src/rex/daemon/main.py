import asyncio
import logging
import os
import signal
from pathlib import Path

logger = logging.getLogger(__name__)


def get_socket_path() -> Path:
    """Resolve socket Path: $XDG_RUNTIME_DIR/rex.sock or /tmp/rex.sock"""
    runtime_user_directory = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_user_directory) / "rex.sock"


class RexDaemon:
    def __init__(self) -> None:
        self._recording: bool = False
        self._server: asyncio.Server | None = None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        # TODO implement dispatch functionality
        try:
            data = await reader.readline()
            logger.debug("received: %s", data.decode().strip())
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve(self, socket_path: Path) -> None:
        if socket_path.exists():
            socket_path.unlink()
        self._server = await asyncio.start_unix_server(self._handle_client, socket_path)
        # owner-only: anyone who can reach this socket can send commands to the daemon
        os.chmod(socket_path, 0o600)
        logger.info("rex is listening on %s", socket_path)
        async with self._server:
            await self._server.serve_forever()

    async def shutdown(self, socket_path: Path) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        if socket_path.exists():
            socket_path.unlink()
            logger.info("removed socket %s", socket_path)


async def _main() -> None:
    socket_path = get_socket_path()
    daemon = RexDaemon()
    loop = asyncio.get_running_loop()

    loop.add_signal_handler(
        signal.SIGINT, lambda: asyncio.create_task(daemon.shutdown(socket_path))
    )
    loop.add_signal_handler(
        signal.SIGTERM, lambda: asyncio.create_task(daemon.shutdown(socket_path))
    )

    await daemon.serve(socket_path)


def run() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(_main())
