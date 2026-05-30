"""WebSocket client for connecting to Live VLM WebUI.

Handles connection, reconnection, and message receiving from the VLM WebUI server.
"""

import json
import logging
import threading
import time
from queue import Queue, Empty
from typing import Optional, Callable, Dict, Any

import websocket


logger = logging.getLogger(__name__)


class VLMWebSocketClient:
    """WebSocket client for Live VLM WebUI."""

    def __init__(
        self,
        url: str = "wss://localhost:8090/ws",
        on_vlm_response: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        reconnect_delay: float = 5.0,
    ):
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL (e.g., wss://localhost:8090/ws)
            on_vlm_response: Callback for VLM response messages. Takes (text, metrics) as arguments.
            reconnect_delay: Delay in seconds before attempting reconnection
        """
        self.url = url
        self.on_vlm_response = on_vlm_response
        self.reconnect_delay = reconnect_delay

        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False

        # Message queue for thread-safe communication
        self.message_queue: Queue = Queue()

        # Track connection status
        self.last_vlm_response_time = 0.0

    def start(self):
        """Start the WebSocket client in a background thread."""
        if self.running:
            logger.warning("WebSocket client already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.thread.start()
        logger.info(f"Started WebSocket client connecting to {self.url}")

    def stop(self):
        """Stop the WebSocket client."""
        logger.info("Stopping WebSocket client...")
        self.running = False

        if self.ws:
            self.ws.close()

        if self.thread:
            self.thread.join(timeout=2.0)

        self.connected = False
        logger.info("WebSocket client stopped")

    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self.connected

    def get_last_response_age(self) -> float:
        """Get time since last VLM response in seconds."""
        if self.last_vlm_response_time == 0.0:
            return float('inf')
        return time.time() - self.last_vlm_response_time

    def _run_websocket(self):
        """Run WebSocket connection loop with automatic reconnection."""
        while self.running:
            try:
                logger.info(f"Connecting to {self.url}...")

                # Create WebSocket connection
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                # Run WebSocket (blocks until closed)
                # For wss://, need to disable SSL verification for self-signed certs
                if self.url.startswith("wss://"):
                    self.ws.run_forever(sslopt={"cert_reqs": 0})
                else:
                    self.ws.run_forever()

            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            # Reconnect after delay if still running
            if self.running:
                logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)

    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        self.connected = True
        logger.info("WebSocket connected successfully")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "vlm_response":
                # VLM analysis response
                text = data.get("text", "")
                metrics = data.get("metrics", {})

                self.last_vlm_response_time = time.time()

                # Call callback if provided
                if self.on_vlm_response:
                    self.on_vlm_response(text, metrics)

                # Log metrics
                last_latency = metrics.get("last_latency_ms", 0)
                total_inferences = metrics.get("total_inferences", 0)
                logger.debug(
                    f"VLM response: {len(text)} chars, "
                    f"latency={last_latency:.0f}ms, "
                    f"total={total_inferences}"
                )

            elif msg_type == "status":
                # Status message
                status_text = data.get("text", "")
                status = data.get("status", "")
                logger.info(f"Status: {status_text} ({status})")

            elif msg_type == "server_config":
                # Server configuration
                model = data.get("model", "unknown")
                api_base = data.get("api_base", "unknown")
                prompt = data.get("prompt", "")
                logger.info(
                    f"Server config: model={model}, api_base={api_base}, "
                    f"prompt_len={len(prompt)}"
                )

            elif msg_type == "gpu_stats":
                # GPU statistics (ignore for now, can log if needed)
                pass

            else:
                logger.debug(f"Received unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse WebSocket message: {message[:100]}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        self.connected = False
        logger.warning(
            f"WebSocket closed: code={close_status_code}, msg={close_msg}"
        )


def main():
    """Test the WebSocket client."""
    logging.basicConfig(level=logging.INFO)

    def on_response(text: str, metrics: Dict[str, Any]):
        """Callback for VLM responses."""
        print(f"\n[VLM Response]")
        print(f"Text ({len(text)} chars): {text[:200]}...")
        print(f"Metrics: {metrics}")

    # Test connection (use ws:// for testing without SSL)
    client = VLMWebSocketClient(
        url="ws://localhost:8090/ws",  # or wss://localhost:8090/ws
        on_vlm_response=on_response,
    )

    try:
        client.start()
        print("WebSocket client started. Press Ctrl+C to stop...")

        # Keep running
        while True:
            time.sleep(1)
            if client.is_connected():
                age = client.get_last_response_age()
                if age != float('inf'):
                    print(f"Last response: {age:.1f}s ago", end='\r')

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        client.stop()


if __name__ == "__main__":
    main()
