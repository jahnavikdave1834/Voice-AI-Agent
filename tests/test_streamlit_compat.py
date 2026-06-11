import pytest

from utilities.streamlit_compat import install_shutdown_guard


def test_shutdown_guard_ignores_closed_event_loop(monkeypatch):
    from streamlit.runtime.runtime import Runtime

    monkeypatch.setattr(
        Runtime,
        "stop",
        lambda self: (_ for _ in ()).throw(RuntimeError("Event loop is closed")),
    )

    install_shutdown_guard()

    Runtime.stop(object())


def test_shutdown_guard_reraises_other_runtime_errors(monkeypatch):
    from streamlit.runtime.runtime import Runtime

    monkeypatch.setattr(
        Runtime,
        "stop",
        lambda self: (_ for _ in ()).throw(RuntimeError("different failure")),
    )

    install_shutdown_guard()

    with pytest.raises(RuntimeError, match="different failure"):
        Runtime.stop(object())
