"""Compatibility helpers for Streamlit runtime behavior."""

from functools import wraps


def install_shutdown_guard() -> None:
    """Make Streamlit shutdown idempotent after its event loop is closed."""
    from streamlit.runtime.runtime import Runtime

    if getattr(Runtime.stop, "_closed_loop_guard", False):
        return

    original_stop = Runtime.stop

    @wraps(original_stop)
    def guarded_stop(self) -> None:
        try:
            original_stop(self)
        except RuntimeError as exc:
            if str(exc) != "Event loop is closed":
                raise

    guarded_stop._closed_loop_guard = True
    Runtime.stop = guarded_stop
