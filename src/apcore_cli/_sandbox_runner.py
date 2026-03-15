"""Entry point for sandboxed module execution (FE-05)."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    module_id = sys.argv[1]
    input_data = json.loads(sys.stdin.read())
    extensions_root = os.environ.get("APCORE_EXTENSIONS_ROOT", "./extensions")

    from apcore import Executor, Registry

    registry = Registry(extensions_dir=extensions_root)
    registry.discover()
    executor = Executor(registry)
    result = executor.call(module_id, input_data)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
