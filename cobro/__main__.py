"""`python -m cobro` opens the app; `python -m cobro cli …` draws without a window (cli.py)."""

from __future__ import annotations

import sys


def _run() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        from cobro.cli import main as cli_main

        return cli_main(sys.argv[2:])
    from cobro.app import main

    return main()


if __name__ == "__main__":
    sys.exit(_run())
