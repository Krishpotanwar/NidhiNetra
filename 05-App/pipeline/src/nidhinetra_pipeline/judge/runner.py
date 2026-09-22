"""Runs the pair judge over the pairs that have no answer yet.

A model and its provider are pinned together: only the pairs listed in PRICES_USD_PER_MILLION can
run, so a routing policy such as `:fastest` or `:cheapest` cannot reach a production run. The
network sits behind `transport`, so everything here is tested without one.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pandas as pd

from . import store
from .inputs import Item
from .rubric import ANSWER_SCHEMA, PROMPT_VERSION, SCHEMA_VERSION, render_messages, response_format
from .verify import check_answer

logger = logging.getLogger("nidhinetra_pipeline.judge.runner")

JUDGE_CODE_VERSION = "pair_judge_code_v1"
ROUTER_URL = "https://router.huggingface.co/{provider}/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_PROVIDER = "deepinfra"
# USD per million tokens, (input, output). A model and provider with no price here cannot run:
# the budget cap would have nothing to count with. Stage D adds the bake-off's pairs.
PRICES_USD_PER_MILLION = {(DEFAULT_MODEL, DEFAULT_PROVIDER): (0.04, 0.17)}
BATCH_SIZE = 15
MAX_OUTPUT_TOKENS = 6000
ATTEMPTS = 4
FLUSH_EVERY = 25  # windows of requests between writes of the judgments file

Transport = Callable[[str, dict[str, str], dict[str, Any]], tuple[int, dict[str, Any]]]


class JudgeError(Exception):
    """The run cannot go on: a pair that may not run, a refused request, or a reply with no cost."""


@dataclass
class Report:
    requests: int = 0
    pairs: int = 0  # pairs sent
    judged: int = 0
    abstained: int = 0  # of the judged, the pairs answered not_enough_detail
    rejected: Counter[str] = field(default_factory=Counter)  # by the rule the answer broke
    no_answer: int = 0  # the reply skipped or garbled them: not stored, asked again next run
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    stopped: str | None = None  # "budget" when the cap ended the run


def http_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    reply = httpx.post(url, headers=headers, json=payload, timeout=120)
    try:
        return reply.status_code, reply.json()
    except ValueError:
        return reply.status_code, {"error": reply.text[:200]}


def _post(
    transport: Transport,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    """The reply body of one request. Rate limits, server errors and dropped connections are
    retried; any other refusal (a bad token, no credit, a parameter the provider rejects) is not."""
    last = "no attempt"
    for attempt in range(ATTEMPTS):
        if attempt:
            sleep(2 ** (attempt - 1))
        try:
            status, body = transport(url, headers, payload)
        except httpx.TransportError as exc:
            last = type(exc).__name__
            continue
        if status == 200:
            return body
        if status != 429 and status < 500:
            raise JudgeError(f"HTTP {status}: {str(body)[:200]}")
        last = f"HTTP {status}"
    raise JudgeError(f"gave up after {ATTEMPTS} attempts ({last})")


def _answers(batch: list[Item], body: dict[str, Any]) -> list[dict[str, Any] | None]:
    """The reply's answer for each item of the batch, None where it gave none."""
    try:
        reply = json.loads(body["choices"][0]["message"]["content"])
        jsonschema.validate(reply, ANSWER_SCHEMA)
    except (KeyError, IndexError, TypeError, ValueError, jsonschema.ValidationError) as exc:
        logger.warning("unreadable reply (%s): %.300s", type(exc).__name__, body)
        return [None] * len(batch)
    by_id: dict[str, dict[str, Any]] = {}
    for answer in reply["answers"]:
        by_id.setdefault(answer["id"], answer)
    return [by_id.get(str(n)) for n in range(1, len(batch) + 1)]


def _row(item: Item, answer: dict[str, Any], stamp: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scope": item.scope,
        "fingerprint_a": item.fingerprint_a,
        "fingerprint_b": item.fingerprint_b,
        "input_fingerprint": item.input_fingerprint,
        **stamp,
    }
    reason = check_answer(item, answer)
    if reason:
        empty = dict.fromkeys(("relation", "asset_a", "place_a", "asset_b", "place_b"))
        return {**row, **empty, "status": "rejected", "rejection": reason}
    quotes = {name: answer[name] for name in ("asset_a", "place_a", "asset_b", "place_b")}
    return {**row, **quotes, "status": "judged", "relation": answer["relation"], "rejection": None}


def _stamp(model_id: str, provider_id: str) -> dict[str, str]:
    if (model_id, provider_id) not in PRICES_USD_PER_MILLION:
        raise JudgeError(
            f"{model_id} on {provider_id} is not a pinned model and provider with a price; "
            "add the pair to PRICES_USD_PER_MILLION (never route by :fastest or :cheapest)"
        )
    return {
        "model_id": model_id,
        "provider_id": provider_id,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "judge_code_version": JUDGE_CODE_VERSION,
    }


def pending(
    items: list[Item],
    store_path: Path,
    model_id: str,
    provider_id: str,
    limit: int | None = None,
) -> list[Item]:
    """The items with no answer yet from this model and provider. With a limit, that many spread
    evenly through them, so a small trial run is not one constituency's pairs."""
    done = store.answered(store.read_judgments(store_path), _stamp(model_id, provider_id))
    todo = [
        i
        for i in items
        if (i.scope, i.fingerprint_a, i.fingerprint_b, i.input_fingerprint) not in done
    ]
    if limit is not None:
        todo = todo[:: max(1, len(todo) // limit)][:limit]
    return todo


def run_judge(
    items: list[Item],
    *,
    store_path: Path,
    model_id: str,
    provider_id: str,
    token: str,
    max_usd: float,
    limit: int | None = None,
    transport: Transport = http_transport,
    workers: int = 1,
    batch_size: int = BATCH_SIZE,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Report:
    """Ask the model about every pending item and store what comes back.

    Stops once the money spent reaches `max_usd`, so the last window of requests can overshoot it
    by their own cost. Whatever was answered is stored even when a request fails, so a rerun
    carries on from there.
    """
    stamp = _stamp(model_id, provider_id)
    price_in, price_out = PRICES_USD_PER_MILLION[(model_id, provider_id)]
    todo = pending(items, store_path, model_id, provider_id, limit)
    batches = [todo[n : n + batch_size] for n in range(0, len(todo), batch_size)]
    url = ROUTER_URL.format(provider=provider_id)
    headers = {"Authorization": f"Bearer {token}"}
    stamp["run_timestamp"] = now().isoformat(timespec="seconds")
    frame = store.read_judgments(store_path)
    rows: list[dict[str, Any]] = []
    report = Report()

    def ask(batch: list[Item]) -> tuple[list[dict[str, Any] | None], int, int]:
        payload = {
            "model": model_id,
            "messages": render_messages(batch),
            "temperature": 0,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": response_format(),
        }
        body = _post(transport, url, headers, payload, sleep)
        try:
            usage = body["usage"]
            return (
                _answers(batch, body),
                int(usage["prompt_tokens"]),
                int(usage["completion_tokens"]),
            )
        except (KeyError, TypeError, ValueError):
            raise JudgeError("a reply carried no token usage, so its cost is unknown") from None

    def flush() -> None:
        nonlocal frame
        if rows:
            new = pd.DataFrame(rows, columns=store.COLUMNS)
            frame = new if frame.empty else pd.concat([frame, new], ignore_index=True)
            store.write_judgments(frame, store_path)
            rows.clear()

    try:
        with ThreadPoolExecutor(workers) as pool:
            for windows, start in enumerate(range(0, len(batches), workers), 1):
                if report.cost_usd >= max_usd:
                    report.stopped = "budget"
                    break
                window = batches[start : start + workers]
                for batch, (answers, sent, received) in zip(
                    window, pool.map(ask, window), strict=True
                ):
                    report.requests += 1
                    report.pairs += len(batch)
                    report.prompt_tokens += sent
                    report.completion_tokens += received
                    report.cost_usd += (sent * price_in + received * price_out) / 1_000_000
                    for item, answer in zip(batch, answers, strict=True):
                        if answer is None:
                            report.no_answer += 1
                            continue
                        row = _row(item, answer, stamp)
                        rows.append(row)
                        if row["status"] == "rejected":
                            report.rejected[row["rejection"]] += 1
                            continue
                        report.judged += 1
                        if row["relation"] == "not_enough_detail":
                            report.abstained += 1
                if windows % FLUSH_EVERY == 0:
                    flush()
                    logger.info("%d pairs asked, $%.4f spent", report.pairs, report.cost_usd)
    finally:
        flush()
    return report
