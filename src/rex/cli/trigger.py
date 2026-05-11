import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_socket_path() -> Path:
    runtime_user_directory = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_user_directory) / "rex.sock"


async def socket_connection(command: str) -> None:
    socket_path = get_socket_path()
    _, writer = await asyncio.open_unix_connection(str(socket_path))
    logger.debug("sending %s to %s", command, socket_path)

    writer.write(f"{command}\n".encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("start", "stop"):
        print("usage: rex-trigger <start|stop>", file=sys.stderr)
        sys.exit(1)
    command = sys.argv[1]
    try:
        asyncio.run(socket_connection(command))
    except FileNotFoundError:
        print("rex is not running", file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        print("rex daemon refused connection", file=sys.stderr)
        sys.exit(1)
