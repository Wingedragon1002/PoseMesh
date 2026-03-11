import cv2
import threading
import numpy as np
import time


class CameraCapture:
    """
    Thread-buffered camera capture. Supports:
    - USB webcam: source = int (device index, e.g. 0, 1, 2)
    - Phone/IP cam: source = str URL (e.g. 'http://192.168.1.x:8080/video')

    Uses a background thread so frame reads never block the main loop.

    Transform parameters (applied after capture, before returning frame):
    - rotation: degrees clockwise (0, 90, 180, 270, or any arbitrary float)
    - zoom: crop factor. 1.0 = no change. < 1.0 = zoom out (show more).
            > 1.0 = zoom in (show less). e.g. 0.6 = show 60% of frame = zoom out.
    """

    def __init__(self, source, label: str = "camera", width: int = 640, height: int = 480,
                 rotation: float = 0.0, zoom: float = 1.0, protocol: str = "tcp"):
        # For IP cameras, rewrite URL scheme based on protocol
        if isinstance(source, str) and source.startswith("http://") and protocol == "udp":
            source = source.replace("http://", "udp://", 1)
        elif isinstance(source, str) and source.startswith("udp://") and protocol == "tcp":
            source = source.replace("udp://", "http://", 1)
        self.source = source
        self.label = label
        self.width = width
        self.height = height
        self.rotation = rotation   # degrees clockwise
        self.zoom = max(0.1, zoom) # crop factor, clamped to avoid divide-by-zero

        self._cap: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_frame_time = 0.0

        # Rolling FPS counter (capture thread only)
        self._fps: float = 0.0
        self._fps_frame_count: int = 0
        self._fps_timer: float = 0.0

    def start(self):
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            raise RuntimeError(f"[Camera:{self.label}] Failed to open source: {self.source}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimize latency

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print(f"[Camera:{self.label}] Started — source: {self.source}")

    def _apply_transform(self, frame: np.ndarray) -> np.ndarray:
        """Apply rotation and zoom to a frame."""
        h, w = frame.shape[:2]

        # ── Zoom (center crop) ──
        z = self.zoom
        if z != 1.0:
            if z < 1.0:
                # Zoom out: crop to center z*w x z*h, then scale back up
                cw = int(w * z)
                ch = int(h * z)
                x0 = (w - cw) // 2
                y0 = (h - ch) // 2
                frame = frame[y0:y0+ch, x0:x0+cw]
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
            else:
                # Zoom in: crop center 1/z fraction
                factor = 1.0 / z
                cw = int(w * factor)
                ch = int(h * factor)
                x0 = (w - cw) // 2
                y0 = (h - ch) // 2
                frame = frame[y0:y0+ch, x0:x0+cw]
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)

        # ── Rotation (90° increments only) ──
        r = int(self.rotation) % 360
        if r == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif r == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif r == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def _capture_loop(self):
        self._fps_timer = time.time()
        self._fps_frame_count = 0
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                frame = self._apply_transform(frame)
                now = time.time()
                with self._lock:
                    self._frame = frame
                    self._last_frame_time = now
                self._fps_frame_count += 1
                elapsed = now - self._fps_timer
                if elapsed >= 1.0:
                    self._fps = self._fps_frame_count / elapsed
                    self._fps_frame_count = 0
                    self._fps_timer = now
            else:
                time.sleep(0.01)

    @property
    def fps(self) -> float:
        """Raw capture FPS (updated every ~1 second)."""
        return self._fps

    def read(self) -> np.ndarray | None:
        """Return the latest frame, or None if not yet available."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def is_fresh(self, max_age_seconds: float = 0.5) -> bool:
        """Returns True if a frame was received recently."""
        return (time.time() - self._last_frame_time) < max_age_seconds

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
        print(f"[Camera:{self.label}] Stopped.")
