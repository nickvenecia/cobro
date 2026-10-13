"""`python -m saldo` opens the app; `python -m saldo cli …` draws without a window (cli.py)."""

from __future__ import annotations

import sys


def _run() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        from saldo.cli import main as cli_main

        return cli_main(sys.argv[2:])
    from saldo.app import main

    return main()


if __name__ == "__main__":
    sys.exit(_run())
