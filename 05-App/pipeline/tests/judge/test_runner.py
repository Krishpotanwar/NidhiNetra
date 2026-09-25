"""Tests for running the pair judge. A stand-in provider replaces the network."""

from __future__ import annotations

import json
import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
from nidhinetra_pipeline.judge import runner, store
from nidhinetra_pipeline.judge.inputs import Item

Reply = tuple[int, dict[str, Any]]


def _items(count: int) -> list[Item]:
    return [
        Item(
            "C1",
            f"a{n:03d}",
            f"b{n:03d}",
            f"Road {n} at Rampur",
            f"Road {n} at Rampur Kalan",
            "Roads",
            "Roads",
            f"i{n:03d}",
        )
        for n in range(count)
    ]


def _answer(pair_id: str, **overrides: Any) -> dict[str, Any]:
    answer = {
        "id": pair_id,
        "relation": "same_asset_different_place",
        "asset_a": "Road",
        "place_a": "Rampur",
        "asset_b": "Road",
        "place_b": "Rampur Kalan",
    }
    return {**answer, **overrides}


def _pair_ids(payload: dict[str, Any]) -> list[str]:
    return [pair["id"] for pair in json.loads(payload["messages"][1]["content"])["pairs"]]


def _body(content: str | None, usage: dict[str, int] | None = None) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 200},
    }


def _reply(
    payload: dict[str, Any],
    answers: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
) -> Reply:
    """A good reply: an answer for every pair in the request, and the tokens it cost."""
    if answers is None:
        answers = [_answer(pair_id) for pair_id in _pair_ids(payload)]
    return 200, _body(json.dumps({"answers": answers}), usage)


def _cents(payload: dict[str, Any]) -> Reply:
    """A good reply that costs exactly 4 cents at the default model's prices."""
    return _reply(payload, usage={"prompt_tokens": 1_000_000, "completion_tokens": 0})


class Provider:
    """Stands in for the router. `handler(n, payload)` answers request number n."""

    def __init__(self, handler: Callable[[int, dict[str, Any]], Reply] | None = None) -> None:
        self.handler = handler or (lambda n, payload: _reply(payload))
        self.requests: list[tuple[str, dict[str, str], dict[str, Any]]] = []

    def __call__(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> Reply:
        self.requests.append((url, headers, payload))
        return self.handler(len(self.requests), payload)


def _run(tmp_path: Path, items: list[Item], provider: Provider, **overrides: Any) -> runner.Report:
    settings: dict[str, Any] = {
        "store_path": tmp_path / "judgments.parquet",
        "model_id": runner.DEFAULT_MODEL,
        "provider_id": runner.DEFAULT_PROVIDER,
        "token": "hf_test",
        "max_usd": 100.0,
        "transport": provider,
        "sleep": lambda seconds: None,
        **overrides,
    }
    return runner.run_judge(items, **settings)


def _stored(tmp_path: Path) -> pd.DataFrame:
    return store.read_judgments(tmp_path / "judgments.parquet")


class TestRun:
    def test_every_pending_pair_is_asked_in_batches_and_stored(self, tmp_path: Path) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(40), provider)

        assert [len(_pair_ids(payload)) for _, _, payload in provider.requests] == [15, 15, 10]
        assert (report.requests, report.pairs, report.judged, report.no_answer) == (3, 40, 40, 0)
        assert dict(report.rejected) == {}
        assert report.stopped is None
        frame = _stored(tmp_path)
        assert len(frame) == 40
        assert set(frame["status"]) == {"judged"}
        assert set(frame["relation"]) == {"same_asset_different_place"}

    def test_an_abstention_is_a_judged_answer_and_is_also_counted_on_its_own(
        self, tmp_path: Path
    ) -> None:
        def mostly_vague(n: int, payload: dict[str, Any]) -> Reply:
            answers = [
                _answer("1", relation="not_enough_detail", asset_a=None, place_a=None),
                _answer("2"),
                _answer("3", relation="not_enough_detail", asset_b=None, place_b=None),
            ]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(3), Provider(mostly_vague))

        assert (report.judged, report.abstained) == (3, 2)
        assert _stored(tmp_path)["relation"].tolist().count("not_enough_detail") == 2

    def test_the_tokens_and_the_cost_are_added_up_from_the_replies(self, tmp_path: Path) -> None:
        usage = {"prompt_tokens": 2_000_000, "completion_tokens": 1_000_000}
        provider = Provider(lambda n, payload: _reply(payload, usage=usage))

        report = _run(tmp_path, _items(20), provider)

        assert (report.prompt_tokens, report.completion_tokens) == (4_000_000, 2_000_000)
        assert report.cost_usd == pytest.approx(2 * (2 * 0.04 + 1 * 0.17))

    def test_a_rerun_asks_for_nothing_it_already_has(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(40), Provider())
        again = Provider()

        report = _run(tmp_path, _items(40), again)

        assert again.requests == []
        assert (report.requests, report.pairs) == (0, 0)
        assert len(_stored(tmp_path)) == 40

    def test_a_pair_whose_input_changed_is_asked_again(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(3), Provider())
        changed = _items(3)
        changed[1] = replace(changed[1], input_fingerprint="moved")
        again = Provider()

        _run(tmp_path, changed, again)

        assert len(again.requests) == 1
        assert len(_pair_ids(again.requests[0][2])) == 1
        assert len(_stored(tmp_path)) == 4

    def test_answers_are_matched_to_their_pair_by_id_not_by_position(self, tmp_path: Path) -> None:
        def backwards(n: int, payload: dict[str, Any]) -> Reply:
            relations = {
                "1": "unrelated",
                "2": "not_enough_detail",
                "3": "same_asset_different_place",
            }
            answers = [_answer(i, relation=relations[i]) for i in ("3", "2", "1")]
            return _reply(payload, answers)

        _run(tmp_path, _items(3), Provider(backwards))

        assert _stored(tmp_path)["relation"].tolist() == [
            "unrelated",
            "not_enough_detail",
            "same_asset_different_place",
        ]

    def test_the_first_answer_for_an_id_is_the_one_kept(self, tmp_path: Path) -> None:
        def twice(n: int, payload: dict[str, Any]) -> Reply:
            answers = [
                _answer("1", relation="unrelated"),
                _answer("1", relation="not_enough_detail"),
            ]
            return _reply(payload, answers)

        _run(tmp_path, _items(1), Provider(twice))

        assert _stored(tmp_path)["relation"].tolist() == ["unrelated"]

    def test_an_answer_for_a_pair_that_was_not_asked_is_ignored(self, tmp_path: Path) -> None:
        def extra(n: int, payload: dict[str, Any]) -> Reply:
            answers = [_answer("1"), _answer("2"), _answer("99", relation="unrelated")]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(2), Provider(extra))

        assert (report.judged, report.no_answer) == (2, 0)
        assert set(_stored(tmp_path)["relation"]) == {"same_asset_different_place"}

    def test_the_request_is_the_one_the_provider_documents(self, tmp_path: Path) -> None:
        provider = Provider()

        _run(tmp_path, _items(2), provider, token="hf_abc")

        ((url, headers, payload),) = provider.requests
        assert url == "https://router.huggingface.co/v1/chat/completions"
        assert headers == {"Authorization": "Bearer hf_abc"}
        assert payload["model"] == "openai/gpt-oss-120b:deepinfra"
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == runner.MAX_OUTPUT_TOKENS
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert [m["role"] for m in payload["messages"]] == ["system", "user"]

    def test_every_row_says_what_produced_it(self, tmp_path: Path) -> None:
        moment = datetime(2026, 9, 22, 10, 30, tzinfo=UTC)

        _run(tmp_path, _items(2), Provider(), now=lambda: moment)

        row = _stored(tmp_path).iloc[0]
        assert row["model_id"] == "openai/gpt-oss-120b"
        assert row["provider_id"] == "deepinfra"
        assert row["prompt_version"] == "pair_judge_prompt_v1"
        assert row["schema_version"] == "pair_judge_schema_v1"
        assert row["judge_code_version"] == runner.JUDGE_CODE_VERSION
        assert row["run_timestamp"] == "2026-09-22T10:30:00+00:00"
        assert (row["scope"], row["fingerprint_a"], row["input_fingerprint"]) == (
            "C1",
            "a000",
            "i000",
        )

    def test_the_token_is_never_stored_or_reported(self, tmp_path: Path) -> None:
        report = _run(tmp_path, _items(3), Provider(), token="hf_SECRET_TOKEN")

        assert len(_stored(tmp_path)) == 3
        assert b"hf_SECRET_TOKEN" not in (tmp_path / "judgments.parquet").read_bytes()
        assert "hf_SECRET_TOKEN" not in repr(report)

    def test_a_limit_runs_only_that_many_pairs(self, tmp_path: Path) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(100), provider, limit=20)

        assert (report.requests, report.pairs) == (2, 20)

    def test_workers_send_a_window_of_requests_together_and_all_of_it_is_stored(
        self, tmp_path: Path
    ) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(50), provider, workers=3)

        assert (report.requests, report.judged) == (4, 50)
        assert len(_stored(tmp_path)) == 50


class TestEvidence:
    def test_an_answer_whose_quote_is_not_in_the_text_is_stored_as_unjudged(
        self, tmp_path: Path
    ) -> None:
        def one_bad(n: int, payload: dict[str, Any]) -> Reply:
            answers = [_answer("1"), _answer("2", place_a="Nowhere"), _answer("3")]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(3), Provider(one_bad))

        assert (report.judged, dict(report.rejected)) == (2, {"place_a_not_in_text": 1})
        frame = _stored(tmp_path)
        rejected = frame[frame["status"] == "rejected"].iloc[0]
        assert rejected["rejection"] == "place_a_not_in_text"
        assert rejected["fingerprint_a"] == "a001"
        assert pd.isna(rejected["relation"])
        assert all(pd.isna(rejected[name]) for name in ("asset_a", "place_a", "asset_b", "place_b"))

    def test_a_rejected_pair_is_not_paid_for_again(self, tmp_path: Path) -> None:
        bad = Provider(lambda n, payload: _reply(payload, [_answer("1", place_b="Nowhere")]))
        _run(tmp_path, _items(1), bad)
        again = Provider()

        _run(tmp_path, _items(1), again)

        assert again.requests == []

    def test_a_pair_the_reply_skips_is_not_stored_and_is_asked_again(self, tmp_path: Path) -> None:
        skipping = Provider(lambda n, payload: _reply(payload, [_answer("1"), _answer("3")]))

        report = _run(tmp_path, _items(3), skipping)

        assert (report.judged, report.no_answer) == (2, 1)
        assert set(_stored(tmp_path)["fingerprint_a"]) == {"a000", "a002"}
        again = Provider()
        _run(tmp_path, _items(3), again)
        assert len(_pair_ids(again.requests[0][2])) == 1

    @pytest.mark.parametrize(
        "body",
        [
            _body("this is not json"),
            _body('{"answers": "none"}'),
            _body("[]"),
            _body(None),
            {"choices": [], "usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            {"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
        ],
        ids=["prose", "wrong shape", "a list", "no content", "no choices", "no choices key"],
    )
    def test_an_unreadable_reply_stores_nothing_for_its_batch(
        self, tmp_path: Path, body: dict[str, Any]
    ) -> None:
        report = _run(tmp_path, _items(4), Provider(lambda n, payload: (200, body)))

        assert (report.judged, report.no_answer, report.requests) == (0, 4, 1)
        assert _stored(tmp_path).empty

    def test_an_unreadable_reply_is_logged_so_a_trial_run_can_be_diagnosed(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        body = _body("the model wrote prose instead of json")

        with caplog.at_level(logging.WARNING, logger="nidhinetra_pipeline.judge.runner"):
            _run(tmp_path, _items(2), Provider(lambda n, payload: (200, body)))

        assert "JSONDecodeError" in caplog.text
        assert "the model wrote prose instead of json" in caplog.text


class TestBudget:
    def test_the_run_stops_once_the_money_spent_reaches_the_cap(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.04)

        assert (report.requests, report.stopped) == (1, "budget")
        assert report.cost_usd == pytest.approx(0.04)
        assert len(_stored(tmp_path)) == 15

    def test_the_run_goes_on_while_the_cap_is_not_reached(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.05)

        assert (report.requests, report.stopped) == (2, "budget")

    def test_a_cap_that_is_never_reached_does_not_stop_the_run(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.13)

        assert (report.requests, report.stopped) == (3, None)

    def test_with_workers_the_cap_is_checked_between_windows(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(60), provider, max_usd=0.04, workers=2)

        assert (report.requests, report.stopped) == (2, "budget")


class TestFailures:
    def test_an_interrupted_run_keeps_what_it_got_and_a_rerun_carries_on(
        self, tmp_path: Path
    ) -> None:
        def refused(n: int, payload: dict[str, Any]) -> Reply:
            return (401, {"error": "bad token"}) if n == 2 else _reply(payload)

        with pytest.raises(runner.JudgeError, match="HTTP 401"):
            _run(tmp_path, _items(40), Provider(refused))
        assert len(_stored(tmp_path)) == 15

        rest = Provider()
        _run(tmp_path, _items(40), rest)

        assert [len(_pair_ids(payload)) for _, _, payload in rest.requests] == [15, 10]
        assert len(_stored(tmp_path)) == 40

    def test_a_reply_with_no_token_usage_stops_the_run_and_is_not_stored(
        self, tmp_path: Path
    ) -> None:
        def no_usage(n: int, payload: dict[str, Any]) -> Reply:
            if n == 2:
                return 200, {"choices": [{"message": {"content": '{"answers": []}'}}]}
            return _reply(payload)

        with pytest.raises(runner.JudgeError, match="no token usage"):
            _run(tmp_path, _items(20), Provider(no_usage))

        assert len(_stored(tmp_path)) == 15

    def test_rate_limits_and_server_errors_are_retried_after_a_growing_pause(
        self, tmp_path: Path
    ) -> None:
        pauses: list[float] = []

        def flaky(n: int, payload: dict[str, Any]) -> Reply:
            return {1: (429, {}), 2: (500, {})}.get(n) or _reply(payload)

        provider = Provider(flaky)

        report = _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), report.judged) == (3, 2)
        assert pauses == [1, 2]

    def test_a_dropped_connection_is_retried(self, tmp_path: Path) -> None:
        def drops(n: int, payload: dict[str, Any]) -> Reply:
            if n == 1:
                raise httpx.ConnectError("connection reset")
            return _reply(payload)

        provider = Provider(drops)

        report = _run(tmp_path, _items(2), provider)

        assert (len(provider.requests), report.judged) == (2, 2)

    def test_it_gives_up_after_four_attempts(self, tmp_path: Path) -> None:
        pauses: list[float] = []
        provider = Provider(lambda n, payload: (503, {}))

        with pytest.raises(runner.JudgeError, match="gave up after 4 attempts"):
            _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), pauses) == (4, [1, 2, 4])

    @pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
    def test_any_other_refusal_is_not_retried(self, tmp_path: Path, status: int) -> None:
        pauses: list[float] = []
        provider = Provider(lambda n, payload: (status, {"error": "no"}))

        with pytest.raises(runner.JudgeError, match=f"HTTP {status}"):
            _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), pauses) == (1, [])


class TestPinning:
    @pytest.mark.parametrize(
        ("model", "provider"),
        [
            ("openai/gpt-oss-120b:cheapest", "deepinfra"),
            ("openai/gpt-oss-120b:fastest", "deepinfra"),
            ("openai/gpt-oss-120b", "auto"),
            ("openai/gpt-oss-120b", "novita"),
            ("openai/gpt-oss-20b", "deepinfra"),
        ],
    )
    def test_only_a_model_and_provider_pinned_together_with_a_price_can_run(
        self, tmp_path: Path, model: str, provider: str
    ) -> None:
        stand_in = Provider()

        with pytest.raises(runner.JudgeError, match="pinned model and provider"):
            _run(tmp_path, _items(2), stand_in, model_id=model, provider_id=provider)
        with pytest.raises(runner.JudgeError, match="pinned model and provider"):
            runner.pending(_items(2), tmp_path / "j.parquet", model, provider)

        assert stand_in.requests == []


class TestPending:
    MODEL, PROVIDER = runner.DEFAULT_MODEL, runner.DEFAULT_PROVIDER

    def _pending(self, tmp_path: Path, count: int, limit: int | None) -> list[str]:
        items = runner.pending(
            _items(count), tmp_path / "judgments.parquet", self.MODEL, self.PROVIDER, limit
        )
        return [item.fingerprint_a for item in items]

    def test_a_limit_takes_pairs_spread_evenly_through_the_pending_ones(
        self, tmp_path: Path
    ) -> None:
        assert self._pending(tmp_path, 100, 10) == [f"a{n:03d}" for n in range(0, 100, 10)]

    def test_a_limit_that_does_not_divide_the_pending_count_still_takes_no_more_than_that(
        self, tmp_path: Path
    ) -> None:
        assert self._pending(tmp_path, 95, 10) == [f"a{n:03d}" for n in range(0, 90, 9)]

    def test_a_limit_above_the_pending_count_takes_them_all(self, tmp_path: Path) -> None:
        assert len(self._pending(tmp_path, 5, 10)) == 5

    def test_a_limit_only_counts_pairs_without_an_answer(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(50), Provider())

        taken = self._pending(tmp_path, 100, 10)

        assert len(taken) == 10
        assert min(taken) >= "a050"

    def test_no_limit_means_every_pair_without_an_answer(self, tmp_path: Path) -> None:
        assert len(self._pending(tmp_path, 100, None)) == 100


class _Echo(BaseHTTPRequestHandler):
    """A one-route server: echoes what it was sent, or breaks when asked to."""

    def do_POST(self) -> None:
        sent = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if sent.get("break"):
            status, kind, body = 502, "text/plain", b"upstream broke"
        elif sent.get("refuse"):
            status, kind, body = 402, "application/json", b'{"error": "no credit"}'
        else:
            echo = {
                "path": self.path,
                "auth": self.headers["Authorization"],
                "type": self.headers["Content-Type"],
                "sent": sent,
            }
            status, kind, body = 200, "application/json", json.dumps(echo).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def echo_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


class TestHttpTransport:
    def test_it_posts_the_payload_as_json_with_the_headers_to_the_url(self, echo_server) -> None:
        payload = {"pairs": ["स्कूल"], "n": 1}

        status, body = runner.http_transport(
            f"{echo_server}/deepinfra/v1/chat/completions", {"Authorization": "Bearer t"}, payload
        )

        assert status == 200
        assert body == {
            "path": "/deepinfra/v1/chat/completions",
            "auth": "Bearer t",
            "type": "application/json",
            "sent": payload,
        }

    def test_a_refusal_comes_back_with_its_status_and_body(self, echo_server) -> None:
        status, body = runner.http_transport(echo_server, {}, {"refuse": True})

        assert (status, body) == (402, {"error": "no credit"})

    def test_a_reply_that_is_not_json_comes_back_as_an_error_text(self, echo_server) -> None:
        status, body = runner.http_transport(echo_server, {}, {"break": True})

        assert (status, body) == (502, {"error": "upstream broke"})

    def test_a_refused_connection_raises_the_error_the_runner_retries(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            closed_port = probe.getsockname()[1]

        with pytest.raises(httpx.TransportError):
            runner.http_transport(f"http://127.0.0.1:{closed_port}", {}, {})
