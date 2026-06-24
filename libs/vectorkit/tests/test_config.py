"""Tests for config loading. These run without the SDK or a robot."""

from vectorkit import RobotConfig


def test_from_env_reads_variables(monkeypatch):
    monkeypatch.setenv("VECTOR_SERIAL", "00e20142")
    monkeypatch.setenv("VECTOR_IP", "192.168.1.50")
    monkeypatch.setenv("VECTOR_NAME", "Vector-A1B2")

    cfg = RobotConfig.from_env()

    assert cfg.serial == "00e20142"
    assert cfg.ip == "192.168.1.50"
    assert cfg.name == "Vector-A1B2"


def test_from_env_defaults_to_none(monkeypatch):
    for var in ("VECTOR_SERIAL", "VECTOR_IP", "VECTOR_NAME"):
        monkeypatch.delenv(var, raising=False)

    cfg = RobotConfig.from_env()

    assert cfg.serial is None
    assert cfg.ip is None
    assert cfg.name is None
