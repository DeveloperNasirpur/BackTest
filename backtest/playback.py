"""
backtest.playback — thread-safe playback controller for backtest replay.

BackTest creates one instance per run() call and registers it with trex
so TrexTerminal clients can control playback speed and pause/resume.
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
        Initial speed multiplier.  ``1.0`` = one real second per timeframe
        second (e.g. 1-minute candles play at 1 candle/second).
        ``0`` or negative = maximum speed (no delay between bars).
    """

    def __init__(self, speed: float = 1.0) -> None:
        self._resume   = threading.Event()
        self._resume.set()          # start in play state
        self._speed    = max(0.0, float(speed))
        self._stopped  = False

    # ── Called by the backtest loop ───────────────────────────────────────────

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
        # No delay at max speed
        if self._speed <= 0:
            return
        delay = tf_seconds / self._speed
        # Sleep in 50ms chunks so pause/stop are responsive
        deadline = time.monotonic() + delay
        while time.monotonic() < deadline:
            if not self._resume.is_set():
                self._resume.wait()   # paused mid-sleep → block
            if self._stopped:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

    # ── Called from the trex server thread (async context) ───────────────────

    def pause(self) -> None:
        """Pause replay — wait() will block until resume()."""
        self._resume.clear()

    def resume(self) -> None:
        """Resume replay."""
        self._resume.set()

    def set_speed(self, speed: float) -> None:
        """
        Set replay speed multiplier.

        ``1.0``  = 1 candle per timeframe-second (1-min chart → 1 bar/sec)
        ``60.0`` = 60× real-time  (1-min chart → 1 bar/minute wall-clock)
        ``0``    = maximum speed
        """
        self._speed = max(0.0, float(speed))

    def stop(self) -> None:
        """Signal the loop to stop (called when backtest ends)."""
        self._stopped = True
        self._resume.set()          # unblock any blocking wait()

    # ── Read-only state (for broadcasting to clients) ─────────────────────────

    @property
    def paused(self) -> bool:
        return not self._resume.is_set()

    @property
    def speed(self) -> float:
        return self._speed


__all__ = ["PlaybackController"]
