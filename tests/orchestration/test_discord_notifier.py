"""
Unit tests for Discord notifier.

Tests cover:
- Message sending at different severity levels
- Webhook error handling
- Graceful degradation without webhook
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.notifications.discord import DiscordNotifier

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def notifier_with_webhook() -> DiscordNotifier:
    """Create notifier with webhook configured."""
    return DiscordNotifier(
        webhook_url="https://discord.com/api/webhooks/test",
        timeout=5.0,
    )


@pytest.fixture
def notifier_without_webhook() -> DiscordNotifier:
    """Create notifier without webhook."""
    return DiscordNotifier(webhook_url=None)


# =============================================================================
# MESSAGE SENDING
# =============================================================================


class TestMessageSending:
    """Test message sending at different levels."""

    @patch("httpx.Client")
    def test_send_info_success(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Info message is sent successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_info("Test info")

        assert result is True

    @patch("httpx.Client")
    def test_send_warning_success(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Warning message is sent successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_warning("Test warning")

        assert result is True

    @patch("httpx.Client")
    def test_send_error_success(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Error message is sent successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_error("Test error")

        assert result is True

    @patch("httpx.Client")
    def test_send_critical_success(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Critical message is sent successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_critical("Test critical")

        assert result is True


# =============================================================================
# ERROR HANDLING
# =============================================================================


class TestErrorHandling:
    """Test webhook error handling."""

    @patch("httpx.Client")
    def test_http_error_returns_false(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """HTTP error returns False without raising."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_info("Test")

        assert result is False

    @patch("httpx.Client")
    def test_request_error_returns_false(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Request error returns False without raising."""
        mock_client.return_value.__enter__.return_value.post.side_effect = httpx.RequestError(
            "Connection failed"
        )

        result = notifier_with_webhook.send_info("Test")

        assert result is False

    @patch("httpx.Client")
    def test_rate_limit_returns_false(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Rate limit (429) returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = notifier_with_webhook.send_info("Test")

        assert result is False


# =============================================================================
# GRACEFUL DEGRADATION
# =============================================================================


class TestGracefulDegradation:
    """Test behavior without webhook configured."""

    def test_no_webhook_returns_false(
        self,
        notifier_without_webhook: DiscordNotifier,
    ) -> None:
        """Missing webhook returns False without error."""
        result = notifier_without_webhook.send_info("Test")

        assert result is False

    def test_no_webhook_all_levels(
        self,
        notifier_without_webhook: DiscordNotifier,
    ) -> None:
        """All severity levels return False without webhook."""
        assert notifier_without_webhook.send_info("Test") is False
        assert notifier_without_webhook.send_warning("Test") is False
        assert notifier_without_webhook.send_error("Test") is False
        assert notifier_without_webhook.send_critical("Test") is False


# =============================================================================
# PAYLOAD FORMAT
# =============================================================================


class TestPayloadFormat:
    """Test Discord embed payload format."""

    @patch("httpx.Client")
    def test_embed_includes_required_fields(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Embed includes title, description, color, timestamp, footer."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post = mock_client.return_value.__enter__.return_value.post
        mock_post.return_value = mock_response

        notifier_with_webhook.send_info("Test message")

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        # Verify payload structure
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert "title" in embed
        assert "description" in embed
        assert "color" in embed
        assert "timestamp" in embed
        assert "footer" in embed

    @patch("httpx.Client")
    def test_info_color_is_blue(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Info level uses blue color."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post = mock_client.return_value.__enter__.return_value.post
        mock_post.return_value = mock_response

        notifier_with_webhook.send_info("Test")

        payload = mock_post.call_args[1]["json"]
        assert payload["embeds"][0]["color"] == 3447003  # Blue

    @patch("httpx.Client")
    def test_critical_color_is_dark_red(
        self,
        mock_client: MagicMock,
        notifier_with_webhook: DiscordNotifier,
    ) -> None:
        """Critical level uses dark red color."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post = mock_client.return_value.__enter__.return_value.post
        mock_post.return_value = mock_response

        notifier_with_webhook.send_critical("Test")

        payload = mock_post.call_args[1]["json"]
        assert payload["embeds"][0]["color"] == 10038562  # Dark red
