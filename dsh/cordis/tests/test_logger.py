"""Process-wide Cordis logging switch."""

from dsh.cordis import is_cordis_logging_enabled, set_cordis_logging


def test_cordis_logging_can_be_enabled_and_disabled() -> None:
    previous = is_cordis_logging_enabled()
    try:
        set_cordis_logging(True)
        assert is_cordis_logging_enabled()

        set_cordis_logging(False)
        assert not is_cordis_logging_enabled()
    finally:
        set_cordis_logging(previous)
