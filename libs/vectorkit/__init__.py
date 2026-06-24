"""Shared helpers reused across Vector prototypes.

Keeps robot connection and config handling in one place so prototypes stay
small. See `connection.py`.
"""

__all__ = ["robot_session", "RobotConfig"]

from .connection import RobotConfig, robot_session
