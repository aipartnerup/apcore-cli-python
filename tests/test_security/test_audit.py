"""Tests for AuditLogger (FE-05)."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

from apcore_cli.security.audit import AuditLogger


class TestAuditLogger:
    def test_log_execution_success(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(path=log_path)
        logger.log_execution("math.add", {"a": 5}, "success", 0, 42)
        lines = log_path.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["module_id"] == "math.add"
        assert entry["status"] == "success"
        assert entry["exit_code"] == 0
        assert entry["duration_ms"] == 42

    def test_log_execution_error(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(path=log_path)
        logger.log_execution("math.add", {}, "error", 1, 100)
        entry = json.loads(log_path.read_text().strip())
        assert entry["status"] == "error"
        assert entry["exit_code"] == 1

    def test_log_creates_directory(self, tmp_path):
        log_path = tmp_path / "subdir" / "deep" / "audit.jsonl"
        AuditLogger(path=log_path)
        assert log_path.parent.exists()

    def test_log_input_hash(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(path=log_path)
        logger.log_execution("mod", {"a": 1}, "success", 0, 10)
        logger.log_execution("mod", {"a": 1}, "success", 0, 10)
        logger.log_execution("mod", {"a": 2}, "success", 0, 10)
        lines = log_path.read_text().strip().split("\n")
        hash1 = json.loads(lines[0])["input_hash"]
        hash2 = json.loads(lines[1])["input_hash"]
        hash3 = json.loads(lines[2])["input_hash"]
        assert hash1 == hash2  # Same input → same hash
        assert hash1 != hash3  # Different input → different hash

    def test_log_write_failure_warns(self, tmp_path, caplog):
        log_path = Path("/nonexistent/readonly/audit.jsonl")
        logger = AuditLogger.__new__(AuditLogger)
        logger._path = log_path
        with caplog.at_level(logging.WARNING, logger="apcore_cli.security"):
            logger.log_execution("mod", {}, "success", 0, 10)
        assert "Could not write audit log" in caplog.text

    def test_get_user_fallback(self, monkeypatch):
        monkeypatch.setenv("USER", "testuser")
        logger = AuditLogger.__new__(AuditLogger)
        with patch("os.getlogin", side_effect=OSError):
            result = logger._get_user()
        assert result == "testuser"

    def test_log_entry_format(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(path=log_path)
        logger.log_execution("math.add", {"a": 1}, "success", 0, 42)
        entry = json.loads(log_path.read_text().strip())
        expected_keys = {
            "timestamp",
            "user",
            "module_id",
            "input_hash",
            "status",
            "exit_code",
            "duration_ms",
        }
        assert set(entry.keys()) == expected_keys
