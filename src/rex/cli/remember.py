import sqlite3
import sys

from rex.config import load_config
from rex.daemon.memory import DEFAULT_DB_PATH, delete_fact, get_facts, init_db, save_fact


def _open_db() -> sqlite3.Connection:
    config = load_config()
    db_path = config.memory_db or DEFAULT_DB_PATH
    return init_db(db_path)


def remember_main() -> None:
    args = sys.argv[1:]

    if not args:
        print("usage: rex-remember <fact>", file=sys.stderr)
        print("       rex-remember --list", file=sys.stderr)
        print("       rex-remember --forget <number>", file=sys.stderr)
        sys.exit(1)

    if args[0] == "--list":
        db = _open_db()
        facts = get_facts(db)
        if not facts:
            print("No facts stored.")
        else:
            for i, fact in enumerate(facts, 1):
                print(f"{i}. {fact}")
        return

    if args[0] == "--forget":
        if len(args) < 2:
            print("usage: rex-remember --forget <number>", file=sys.stderr)
            sys.exit(1)
        try:
            idx = int(args[1])
        except ValueError:
            print("--forget expects a number (use --list to see indices)", file=sys.stderr)
            sys.exit(1)
        db = _open_db()
        facts = get_facts(db)
        if idx < 1 or idx > len(facts):
            print(
                f"No fact at index {idx} (--list shows {len(facts)} facts)",
                file=sys.stderr,
            )
            sys.exit(1)
        fact = facts[idx - 1]
        delete_fact(db, fact)
        print(f"Forgotten: {fact}")
        return

    fact = " ".join(args)
    db = _open_db()
    inserted = save_fact(db, fact)
    if inserted:
        print(f"Remembered: {fact}")
    else:
        print(f"Already known: {fact}")
