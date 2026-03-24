import threading
import time


class SharedState:
    """
    Thread-safe shared state across:
    - WebRTC track (producer)
    - API endpoints (consumer)
    """

    def __init__(self):
        self._lock = threading.Lock()

        # latest processed metadata
        self._metadata = {
            "valve": None,
            "warnings": [],
            "multi_person": False,
            "timestamp": None
        }

        # control flags
        self._record_requested = False
        self._record_valve = None

    # ================= METADATA =================
    def update_metadata(self, metadata: dict):
        with self._lock:
            self._metadata = {
                **metadata,
                "timestamp": time.time()
            }

    def get_metadata(self):
        with self._lock:
            return dict(self._metadata)

    # ================= RECORD CONTROL =================
    def request_record(self, valve_name: str):
        with self._lock:
            self._record_requested = True
            self._record_valve = valve_name

    def consume_record_request(self):
        """
        Called by processing loop to act on request
        """
        with self._lock:
            if not self._record_requested:
                return None

            valve = self._record_valve

            # reset after consuming
            self._record_requested = False
            self._record_valve = None

            return valve


# global singleton (simple + effective)
state = SharedState()