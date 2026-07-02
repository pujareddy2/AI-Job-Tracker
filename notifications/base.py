"""
notifications/base.py — Abstract Notifier Interface
===================================================
Purpose
-------
Defines the base contract for all notification channels in the application.

Design Decisions
----------------
- Ensures any future notifier (e.g., Slack, Telegram) implements the same interface.
"""

from __future__ import annotations

import abc
from typing import Any

from job_model.universal_model import UniversalJobModel


class Notifier(abc.ABC):
    """
    Abstract Base Class for notification engines.
    """

    @abc.abstractmethod
    def send_report(self, jobs: list[UniversalJobModel], **kwargs: Any) -> bool:
        """
        Generates and sends a career report notification.

        Args:
            jobs: List of UniversalJobModel instances for the current run.
            **kwargs: Additional configuration args for the notification channel.

        Returns:
            bool: True if the notification was sent successfully, False otherwise.
        """
        pass
