"""system.info — Get system information (macOS/Linux)."""

import os
import platform
import sys

from pydantic import BaseModel


class Input(BaseModel):
    pass


class Output(BaseModel):
    os: str
    os_version: str
    architecture: str
    hostname: str
    python_version: str
    user: str
    cwd: str


class SystemInfo:
    """Get basic system information (OS, Python, hostname)."""

    input_schema = Input
    output_schema = Output
    description = "Get basic system information (OS, Python, hostname)"

    def execute(self, inputs, context=None):
        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": sys.version.split()[0],
            "user": os.getenv("USER", os.getenv("USERNAME", "unknown")),
            "cwd": os.getcwd(),
        }
