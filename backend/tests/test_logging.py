import importlib
import logging
import os
import sys


def _setup_backend_imports():
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def test_non_request_logging_does_not_crash(capsys):
    _setup_backend_imports()
    import logging_config

    importlib.reload(logging_config)
    logging_config.setup_logging()

    logging.getLogger("external").info("hello from external logger")

    captured = capsys.readouterr()
    assert "Logging error" not in captured.err
    assert "hello from external logger" in captured.err
    assert "request_id" in captured.err
