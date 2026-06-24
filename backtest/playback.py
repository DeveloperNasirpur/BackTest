"""
backtest.playback — thread-safe playback controller for backtest replay.
"""
from __future__ import annotations

import threading
import time


class PlaybackController:
    """
    Thread-safe controller for backtest candle replay.

    The backtest loop calls ``wait(tf_seconds)`` after each bar.
    TrexTerminal clients send ``bt_playback`` messages which are routed here
    via trex engine (pause / resume / set_speed).

    Parameters
    ----------
    speed:
        Initial speed multiplier.  ``1.0`` = 1 bar per real second.
        ``0`` = maximum speed (no delay).
    """

    def __init__(self, speed: float = 1.0) -> None:
        self._resume   = threading.Event()
        self._resume.set()                      # start in play state
        self._lock     = threading.Lock()       # guards _speed
        self._speed    = max(0.0, float(speed))
        self._stopped  = False

    # ── Called by the backtest loop (main thread) ─────────────────────────────

    def wait(self, tf_seconds: int) -> None:
        """
        Block until the next bar should be processed.

        - If paused: blocks until resume() is called.
        - Then sleeps for ``tf_seconds / speed`` seconds (0 if speed <= 0).
        - Returns immediately after stop() is called.
        """
        if self._stopped:
            return
        # Block while paused
        self._resume.wait()
        if self._stopped:
            return
        # Read speed atomically
        with self._lock:
            speed = self._speed
        if speed <= 0:
            return
        delay = tf_seconds / speed
        # Sleep in 50 ms chunks — stays responsive to pause/stop/speed changes
        deadline = time.monotonic() + delay
        while time.monotonic() < deadline:
            if not self._resume.is_set():
                self._resume.wait()             # paused mid-sleep → block
            if self._stopped:
                return
            # Re-read speed in case it changed mid-sleep
            with self._lock:
                speed = self._speed
            if speed <= 0:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

    # ── Called from the trex server thread ───────────────────────────────────

    def pause(self) -> None:
        """Pause replay — wait() will block until resume()."""
        self._resume.clear()

    def resume(self) -> None:
        """Resume replay."""
        self._resume.set()

    def set_speed(self, speed: float) -> None:
        """Set replay speed multiplier. Thread-safe."""
        with self._lock:
            self._speed = max(0.0, float(speed))

    def stop(self) -> None:
        """Signal the loop to stop (called when backtest ends)."""
        self._stopped = True
        self._resume.set()                      # unblock any blocking wait()

    # ── Read-only state ───────────────────────────────────────────────────────

    @property
    def paused(self) -> bool:
        return not self._resume.is_set()

    @property
    def speed(self) -> float:
        with self._lock:
            return self._speed


__all__ = ["PlaybackController"]
