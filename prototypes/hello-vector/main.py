"""Hello-world: connect to Vector and prove the pipeline end to end.

Run after wire-pod is up and the SDK is authenticated (docs/setup-vector.md):

    python main.py

Reads robot details from ~/.anki_vector/sdk_config.ini, or from the
VECTOR_SERIAL / VECTOR_IP / VECTOR_NAME environment variables.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly without installing the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "libs"))

from vectorkit import robot_session  # noqa: E402


def main() -> int:
    with robot_session() as robot:
        battery = robot.get_battery_state()
        print(f"Connected. Battery: {battery.battery_volts:.2f}V, level {battery.battery_level}")
        robot.behavior.say_text("Hello. The pipeline works.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
