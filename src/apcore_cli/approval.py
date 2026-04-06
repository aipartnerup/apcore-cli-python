"""Approval Gate — TTY-aware HITL approval (FE-03, FE-11 §3.5)."""

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any

import click

logger = logging.getLogger("apcore_cli.approval")


class ApprovalTimeoutError(Exception):
    """Raised when the approval prompt times out."""

    pass


def _get_annotation(annotations: Any, key: str, default: Any = None) -> Any:
    """Get an annotation value from either a dict or a ModuleAnnotations object."""
    if isinstance(annotations, dict):
        return annotations.get(key, default)
    return getattr(annotations, key, default)


# ---------------------------------------------------------------------------
# CliApprovalHandler — implements apcore ApprovalHandler protocol (FE-11 §3.5)
# ---------------------------------------------------------------------------


class CliApprovalHandler:
    """ApprovalHandler that prompts in TTY, auto-denies in non-TTY (unless bypassed).

    Implements the apcore ApprovalHandler protocol:
    - ``request_approval(request) -> ApprovalResult``
    - ``check_approval(approval_id) -> ApprovalResult``

    Pass to Executor via ``executor.set_approval_handler(handler)``.
    """

    def __init__(self, auto_approve: bool = False, timeout: int = 60) -> None:
        self.auto_approve = auto_approve
        self.timeout = max(1, min(timeout, 3600))

    async def request_approval(self, request: Any) -> Any:
        """Request approval for a module invocation.

        Follows the apcore ApprovalRequest/ApprovalResult protocol.
        Returns a dict with ``status``, ``approved_by``, ``reason`` fields
        (duck-type compatible with ApprovalResult dataclass).
        """
        module_id = getattr(request, "module_id", "unknown")

        # Bypass: auto_approve flag
        if self.auto_approve:
            logger.info("Approval bypassed via --yes flag for module '%s'.", module_id)
            return {"status": "approved", "approved_by": "auto_approve"}

        # Bypass: APCORE_CLI_AUTO_APPROVE env var
        env_val = os.environ.get("APCORE_CLI_AUTO_APPROVE", "")
        if env_val == "1":
            logger.info("Approval bypassed via APCORE_CLI_AUTO_APPROVE for '%s'.", module_id)
            return {"status": "approved", "approved_by": "env_auto_approve"}
        if env_val != "" and env_val != "1":
            logger.warning("APCORE_CLI_AUTO_APPROVE='%s', expected '1'. Ignoring.", env_val)

        # Non-TTY: reject
        if not sys.stdin.isatty():
            return {
                "status": "rejected",
                "reason": "Non-interactive session without --yes",
            }

        # TTY prompt
        annotations = getattr(request, "annotations", None) or {}
        extra = getattr(annotations, "extra", {}) if not isinstance(annotations, dict) else annotations
        message = extra.get("approval_message") or f"Module '{module_id}' requires approval to execute."

        click.echo(message, err=True)
        try:
            approved = _tty_prompt(module_id, self.timeout)
        except ApprovalTimeoutError:
            return {"status": "timeout", "reason": f"Timed out after {self.timeout}s"}

        if approved:
            return {"status": "approved", "approved_by": "tty_user"}
        return {"status": "rejected", "reason": "User rejected"}

    async def check_approval(self, approval_id: str) -> Any:
        """Check status of a previously pending approval (Phase B).

        CLI does not support async approval polling; always returns rejected.
        """
        return {
            "status": "rejected",
            "reason": "CLI does not support async approval polling",
        }


# ---------------------------------------------------------------------------
# Legacy check_approval() — backward-compatible wrapper
# ---------------------------------------------------------------------------


def check_approval(module_def: Any, auto_approve: bool, timeout: int = 60) -> None:
    """Check if module requires approval and handle accordingly.

    Returns None if approved (or approval not required).
    Calls sys.exit(46) if denied/timed out/pending.

    Args:
        module_def: Module descriptor with annotations.
        auto_approve: If True, bypass approval (--yes flag).
        timeout: Approval prompt timeout in seconds.
    """
    annotations = getattr(module_def, "annotations", None)
    if annotations is None or (not isinstance(annotations, dict) and not hasattr(annotations, "requires_approval")):
        return

    requires = _get_annotation(annotations, "requires_approval", False)
    if requires is not True:
        return

    module_id = getattr(module_def, "module_id", getattr(module_def, "canonical_id", "unknown"))

    # Bypass: --yes flag (highest priority)
    if auto_approve is True:
        logger.info("Approval bypassed via --yes flag for module '%s'.", module_id)
        return

    # Bypass: APCORE_CLI_AUTO_APPROVE env var
    env_val = os.environ.get("APCORE_CLI_AUTO_APPROVE", "")
    if env_val == "1":
        logger.info("Approval bypassed via APCORE_CLI_AUTO_APPROVE for '%s'.", module_id)
        return
    if env_val != "" and env_val != "1":
        logger.warning("APCORE_CLI_AUTO_APPROVE='%s', expected '1'. Ignoring.", env_val)

    # Non-TTY check
    if not sys.stdin.isatty():
        click.echo(
            f"Error: Module '{module_id}' requires approval but no interactive "
            "terminal is available. Use --yes or set APCORE_CLI_AUTO_APPROVE=1 "
            "to bypass.",
            err=True,
        )
        sys.exit(46)

    # TTY prompt
    _prompt_with_timeout(module_def, timeout=timeout)


# ---------------------------------------------------------------------------
# Internal prompt implementation
# ---------------------------------------------------------------------------


def _prompt_with_timeout(module_def: Any, timeout: int = 60) -> None:
    """Display approval prompt with timeout."""
    timeout = max(1, min(timeout, 3600))

    module_id = getattr(module_def, "module_id", getattr(module_def, "canonical_id", "unknown"))
    annotations = getattr(module_def, "annotations", None) or {}
    message = _get_annotation(annotations, "approval_message", None)
    if message is None:
        message = f"Module '{module_id}' requires approval to execute."

    click.echo(message, err=True)

    try:
        approved = _tty_prompt(module_id, timeout)
    except ApprovalTimeoutError:
        click.echo(f"Error: Approval prompt timed out after {timeout} seconds.", err=True)
        sys.exit(46)

    if approved:
        logger.info("User approved execution of module '%s'.", module_id)
    else:
        click.echo("Error: Approval denied.", err=True)
        sys.exit(46)


def _tty_prompt(module_id: str, timeout: int) -> bool:
    """Run the TTY prompt with timeout. Returns True if approved, raises on timeout."""
    if sys.platform != "win32":
        return _prompt_unix(module_id, timeout)
    return _prompt_windows(module_id, timeout)


def _prompt_unix(module_id: str, timeout: int) -> bool:
    """Unix approval prompt using SIGALRM."""
    import signal

    def _timeout_handler(signum: int, frame: Any) -> None:
        raise ApprovalTimeoutError()

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout)

    try:
        approved = click.confirm("Proceed?", default=False)
    except ApprovalTimeoutError:
        logger.warning("Approval timed out after %ds for module '%s'.", timeout, module_id)
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    return approved


def _prompt_windows(module_id: str, timeout: int) -> bool:
    """Windows approval prompt using threading.Timer + ctypes."""
    import ctypes

    def _interrupt_main() -> None:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(threading.main_thread().ident),
            ctypes.py_object(ApprovalTimeoutError),
        )

    timer = threading.Timer(timeout, _interrupt_main)
    timer.start()

    try:
        approved = click.confirm("Proceed?", default=False)
        timer.cancel()
        return approved
    except ApprovalTimeoutError:
        timer.cancel()
        logger.warning("Approval timed out after %ds for module '%s'.", timeout, module_id)
        raise
