import asyncio
import logging
import sys
from pathlib import Path

from rex.config import load_config, resolve_socket_path

logger = logging.getLogger(__name__)


def get_socket_path() -> Path:
    config = load_config()
    return resolve_socket_path(config.daemon.socket_path)


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
