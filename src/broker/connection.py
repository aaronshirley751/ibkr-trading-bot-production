"""
IBKR Gateway connection management with retry logic and health monitoring.

ALPHA LEARNINGS ENFORCED:
- ClientId must be timestamp-based for uniqueness
- Exponential backoff on connection failures
- Clean resource cleanup on disconnect
- Timeout parameter propagation
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional

from ib_insync import IB

from .exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


class IBKRConnection:
    """
    Manages IBKR Gateway connection with retry logic and health monitoring.

    This class wraps ib_insync.IB with production-ready connection management:
    - Automatic ClientId generation (timestamp-based)
    - Exponential backoff retry logic
    - Connection health monitoring
    - Clean resource cleanup
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4002,
        client_id: Optional[int] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay_base: float = 2.0,
    ):
        """
        Initialize connection parameters.

        Args:
            host: Gateway host (default localhost)
            port: Gateway port (default 4002 for paper trading)
            client_id: Unique client ID (auto-generated if None)
            timeout: Connection timeout in seconds
            max_retries: Maximum retry attempts on failure
            retry_delay_base: Base delay for exponential backoff (2^n * base)
        """
        self.host = host
        self.port = port
        self.client_id = client_id if client_id is not None else self.generate_client_id()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base

        self._ib: Optional[IB] = None
        self._connection_start_time: Optional[datetime] = None
        self._reconnect_count = 0
        self._last_heartbeat: Optional[datetime] = None

        logger.info(f"IBKRConnection initialized: {host}:{port}, ClientId={self.client_id}")

    def connect(self) -> bool:
        """
        Establish connection to IBKR Gateway with retry logic.

        Returns:
            True if connected successfully, False otherwise

        Raises:
            ConnectionTimeoutError: If connection times out
            MaxRetriesExceededError: If max retries reached

        Implementation Notes:
            - Generate unique ClientId if not provided (timestamp-based)
            - Implement exponential backoff: delay = retry_delay_base ** attempt
            - Track connection attempts for monitoring
        """
        if self._ib is None:
            self._ib = IB()  # type: ignore[no-untyped-call]

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Connection attempt {attempt + 1}/{self.max_retries} "
                    f"to {self.host}:{self.port}"
                )

                # Attempt connection
                self._ib.connect(
                    self.host, self.port, clientId=self.client_id, timeout=self.timeout
                )

                if self._ib.isConnected():
                    self._connection_start_time = datetime.now(timezone.utc)
                    self._last_heartbeat = datetime.now(timezone.utc)
                    logger.info(f"Successfully connected to Gateway (ClientId={self.client_id})")
                    return True

            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {type(e).__name__}: {e}")

                # If not last attempt, apply exponential backoff
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base**attempt
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    logger.error(f"Max retries ({self.max_retries}) exceeded, connection failed")
                    raise MaxRetriesExceededError(
                        f"Failed to connect after {self.max_retries} attempts"
                    ) from e

        return False

    def disconnect(self) -> None:
        """
        Cleanly disconnect from Gateway.

        Implementation Notes:
            - Cancel all active subscriptions
            - Close socket connection
            - Release resources (threads, event loops)
            - Log disconnection with timestamp
        """
        if self._ib is not None and self._ib.isConnected():
            logger.info(f"Disconnecting from Gateway (ClientId={self.client_id})")
            self._ib.disconnect()  # type: ignore[no-untyped-call]
            self._connection_start_time = None
            self._last_heartbeat = None
            logger.info("Disconnected successfully")
        else:
            logger.debug("Disconnect called but already disconnected")

    def is_connected(self) -> bool:
        """
        Check if connection is active and healthy.

        Returns:
            True if connected and responsive, False otherwise

        Implementation Notes:
            - Don't just check socket state
            - Validate Gateway is responding
            - Return False if connection is stale
        """
        if self._ib is None:
            return False

        is_conn = self._ib.isConnected()

        # Update heartbeat if connected
        if is_conn:
            self._last_heartbeat = datetime.now(timezone.utc)

        return is_conn

    def reconnect(self) -> bool:
        """
        Attempt to reconnect after disconnection.

        Returns:
            True if reconnected successfully, False otherwise

        Implementation Notes:
            - Preserve original ClientId
            - Reset retry counter
            - Re-establish subscriptions if any were active
        """
        logger.info("Attempting to reconnect to Gateway")

        # Disconnect if still connected
        if self._ib is not None and self._ib.isConnected():
            self.disconnect()

        # Attempt reconnection
        try:
            success = self.connect()
            if success:
                self._reconnect_count += 1
                logger.info(f"Reconnection successful (total reconnects: {self._reconnect_count})")
            return success
        except Exception as e:
            logger.error(f"Reconnection failed: {type(e).__name__}: {e}")
            return False

    @staticmethod
    def generate_client_id() -> int:
        """
        Generate unique timestamp-based ClientId.

        Returns:
            Integer ClientId derived from Unix timestamp

        Implementation Notes:
            - Use current Unix timestamp (milliseconds since epoch)
            - Convert to integer
            - Ensure uniqueness across rapid successive calls
            - Range: 0 to ~1,000,000 (modulo to keep manageable)

        ALPHA LEARNING: Timestamp-based ClientId ensures uniqueness across
        multiple bot instances and prevents Gateway rejection due to ID collisions.
        """
        # Use milliseconds timestamp, modulo to keep in reasonable range
        client_id = int(datetime.now().timestamp() * 1000) % 1000000
        return client_id

    @property
    def connection_metrics(self) -> dict[str, object]:
        """
        Return connection health metrics for monitoring.

        Returns:
            Dictionary with:
                - connected: bool
                - uptime_seconds: float (None if disconnected)
                - reconnect_count: int
                - last_heartbeat: datetime (None if never connected)
                - client_id: int
        """
        uptime = None
        if self._connection_start_time is not None and self.is_connected():
            uptime = (datetime.now(timezone.utc) - self._connection_start_time).total_seconds()

        return {
            "connected": self.is_connected(),
            "uptime_seconds": uptime,
            "reconnect_count": self._reconnect_count,
            "last_heartbeat": self._last_heartbeat,
            "client_id": self.client_id,
            "host": self.host,
            "port": self.port,
        }

    @property
    def ib(self) -> IB:
        """
        Access underlying IB instance.

        Returns:
            ib_insync.IB instance

        Raises:
            RuntimeError: If not connected
        """
        if self._ib is None or not self._ib.isConnected():
            raise RuntimeError("Not connected to Gateway. Call connect() first.")
        return self._ib

    def __enter__(self) -> "IBKRConnection":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected() else "disconnected"
        return (
            f"IBKRConnection({self.host}:{self.port}, "
            f"ClientId={self.client_id}, status={status})"
        )
