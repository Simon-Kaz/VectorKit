"""Robot connection helpers.

Thin wrapper over the Vector SDK so prototypes do not each reimplement
config loading and connection setup. The SDK is imported lazily so this
module (and the test suite) imports cleanly without the SDK or a robot
present.

Configuration is read from, in order of precedence:
  1. Explicit arguments to `robot_session`
  2. Environment variables: VECTOR_SERIAL, VECTOR_IP, VECTOR_NAME
  3. The SDK's own `~/.anki_vector/sdk_config.ini` (written by
     `python -m anki_vector.configure`)
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class RobotConfig:
    """Connection details for a single robot.

    Any field left as None falls back to the SDK's stored config.
    """

    serial: str | None = None
    ip: str | None = None
    name: str | None = None

    @classmethod
    def from_env(cls) -> RobotConfig:
        return cls(
            serial=os.environ.get("VECTOR_SERIAL"),
            ip=os.environ.get("VECTOR_IP"),
            name=os.environ.get("VECTOR_NAME"),
        )


@contextmanager
def robot_session(config: RobotConfig | None = None) -> Iterator[object]:
    """Yield a connected Vector robot, closing it on exit.

    Usage:
        from vectorkit import robot_session
        with robot_session() as robot:
            robot.behavior.say_text("hello")

    Raises ImportError with guidance if the SDK is not installed.
    """
    try:
        import anki_vector  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on runtime env
        raise ImportError(
            "The Vector SDK is not installed. Install the vendored fork with "
            "`pip install -e libs/vendor/wirepod-vector-python-sdk`, then run "
            "`python -m anki_vector.configure` to authenticate. "
            "See docs/setup-vector.md."
        ) from exc

    cfg = config or RobotConfig.from_env()
    robot = anki_vector.Robot(
        serial=cfg.serial,
        ip=cfg.ip,
        name=cfg.name,
    )
    robot.connect()
    try:
        yield robot
    finally:
        robot.disconnect()
