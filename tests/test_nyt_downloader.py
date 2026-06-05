from __future__ import annotations

import io
import unittest
from urllib.error import HTTPError

from iesbhistorico.downloader.nyt_downloader import _request_json_with_backoff


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def rate_limit_error() -> HTTPError:
    return HTTPError(
        url="https://example.com",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(b""),
    )


class NYTDownloaderBackoffTest(unittest.TestCase):
    def test_429_retries_then_success(self) -> None:
        calls = {"count": 0}
        sleeps: list[float] = []

        def opener(_url: str, timeout: int) -> FakeResponse:
            self.assertEqual(timeout, 60)
            calls["count"] += 1
            if calls["count"] <= 2:
                raise rate_limit_error()
            return FakeResponse(b'{"ok": true}')

        payload = _request_json_with_backoff(
            "https://example.com",
            max_429_retries=5,
            initial_backoff_seconds=1,
            opener=opener,
            sleeper=sleeps.append,
        )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(calls["count"], 3)
        self.assertEqual(sleeps, [1, 2])

    def test_429_fails_after_ten_retries_by_default(self) -> None:
        calls = {"count": 0}
        sleeps: list[float] = []

        def opener(_url: str, timeout: int) -> FakeResponse:
            calls["count"] += 1
            raise rate_limit_error()

        with self.assertRaises(HTTPError):
            _request_json_with_backoff(
                "https://example.com",
                opener=opener,
                sleeper=sleeps.append,
            )

        self.assertEqual(calls["count"], 11)
        self.assertEqual(sleeps, [20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240])


if __name__ == "__main__":
    unittest.main()
