from __future__ import annotations

import sys

from mudctl.backend import FTPClientBackend
from mudctl.commands import run
from mudctl.output import ExitCode


def main() -> int:
    return run(FTPClientBackend())


if __name__ == "__main__":
    sys.exit(main())