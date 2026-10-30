import httpx
import pytest

from cdm.http import RetryError, make_client, request_with_retry


def client_with(statuses: list[int]) -> tuple[httpx.Client, list[int]]:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = statuses[min(len(calls), len(statuses) - 1)]
        calls.append(status)
        return httpx.Response(status, json={})

    return make_client(httpx.MockTransport(handler)), calls


@pytest.mark.parametrize("transient", [409, 429, 500, 503])
def test_retries_transient_status_then_succeeds(transient):
    client, calls = client_with([transient, transient, 200])
    sleeps: list[float] = []
    response = request_with_retry(client, "GET", "https://example.test", sleep=sleeps.append)
    assert response.status_code == 200
    assert calls == [transient, transient, 200]
    assert len(sleeps) == 2


def test_backoff_delays_stay_within_exponential_cap():
    client, _ = client_with([503])
    sleeps: list[float] = []
    with pytest.raises(RetryError):
        request_with_retry(
            client, "GET", "https://example.test", max_attempts=4, base_delay=1.0,
            sleep=sleeps.append,
        )  # fmt: skip
    assert len(sleeps) == 3
    for attempt, delay in enumerate(sleeps, start=1):
        assert 0 <= delay <= 2 ** (attempt - 1)


def test_client_error_is_not_retried():
    client, calls = client_with([404])
    with pytest.raises(httpx.HTTPStatusError):
        request_with_retry(client, "GET", "https://example.test", sleep=lambda _: None)
    assert calls == [404]


def test_transport_error_is_retried():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200)

    client = make_client(httpx.MockTransport(handler))
    assert request_with_retry(client, "GET", "https://example.test", sleep=lambda _: None)
    assert len(attempts) == 2
