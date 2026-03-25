from datetime import datetime

from tests.fakes.gateway.time import DEFAULT_FAKE_TIME, FakeTime


def test_now_returns_default_time() -> None:
    fake_time = FakeTime()
    assert fake_time.now() == DEFAULT_FAKE_TIME


def test_now_returns_custom_time() -> None:
    custom = datetime(2025, 6, 15, 10, 0, 0)
    fake_time = FakeTime(current_time=custom)
    assert fake_time.now() == custom


def test_sleep_tracks_calls() -> None:
    fake_time = FakeTime()
    fake_time.sleep(1.5)
    fake_time.sleep(0.5)
    assert fake_time.sleep_calls == [1.5, 0.5]


def test_sleep_calls_initially_empty() -> None:
    fake_time = FakeTime()
    assert fake_time.sleep_calls == []


def test_monotonic_returns_default_zero() -> None:
    fake_time = FakeTime()
    assert fake_time.monotonic() == 0.0


def test_monotonic_returns_fixed_value() -> None:
    fake_time = FakeTime(monotonic_values=[100.0])
    assert fake_time.monotonic() == 100.0
    assert fake_time.monotonic() == 100.0


def test_monotonic_returns_sequence_in_order() -> None:
    fake_time = FakeTime(monotonic_values=[1.0, 2.0, 3.0])
    assert fake_time.monotonic() == 1.0
    assert fake_time.monotonic() == 2.0
    assert fake_time.monotonic() == 3.0


def test_monotonic_repeats_last_value_when_exhausted() -> None:
    fake_time = FakeTime(monotonic_values=[1.0, 5.0])
    assert fake_time.monotonic() == 1.0
    assert fake_time.monotonic() == 5.0
    assert fake_time.monotonic() == 5.0
    assert fake_time.monotonic() == 5.0
