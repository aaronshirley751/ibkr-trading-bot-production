"""
Notifications module for trading system alerts.

Provides Discord webhook integration and other notification channels.
"""

from src.notifications.discord import DiscordNotifier

__all__ = ["DiscordNotifier"]
