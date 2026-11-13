"""Optionally ask the game to upload its own error log.

The client keeps a report log (`Reports`, the "REPORTSMODULE"): among other things, a failed table load
writes `Error loading MST INFO=<details>` to it (LoginScene::procStateMstLoadWait and
procStateTextMstLoadWait). The live servers could ask for that log with a "report back" group in any
reply; the client's report scheduler (`Reports::update`) then uploads it with `sgStoreLogReportRequest`
and waits for a "report state" group in the answer. Read from the Android 9.0 library:

  report back   group 383e98ad (sgReportBackResponse)
                  86f76840  send-after time, "%Y-%m-%d %H:%M:%S" UTC (CommonUtils::convertToTime);
                            "0" means "no request"
                  da99ba05  hold flag; "0" lets the upload go ahead
  store log     request sgStoreLogReportRequest, /actionSymbol/6611dc2f.php, key af7a56a0
  report state  group cd87bd8b (sgReportStateResponse), 950510b8 = 0 for success

This matters for a stock client such as the iPhone app, whose own system log is redacted: its reports
are the only place the client says what went wrong. Collection is off by default; turn on
EXVIUS_CLIENT_REPORTS=1 to save uploads under <server data>/client-reports/. The request is sent on
the first RoutineHomeUpdateRequest after the Home screen loads, not during login, and only once per
profile per server process. Pending uploads are acknowledged and discarded while collection is off.

OFF BY DEFAULT since 2026-11-10. The client can upload its whole log repeatedly (about 22 MB each), so the
request is deferred until the first home update and sent only once per profile while the server is running.
Off, the server asks for nothing; an upload the game already has queued is still answered (report state 0)
but not saved. The per-request records (capture_server) never keep a report's body.
"""
from __future__ import annotations

import json
import os
import threading
import time

REPORT_BACK_GROUP = "383e98ad"
REPORT_BACK_TIME = "86f76840"
REPORT_BACK_HOLD = "da99ba05"
REPORT_STATE_GROUP = "cd87bd8b"
REPORT_STATE_VALUE = "950510b8"
STORE_LOG_REQUEST = "6611dc2f"
CARRIERS = {"Daud71Hn"}   # RoutineHomeUpdateRequest, after login
_REQUESTED_PROFILES: set[str] = set()
_REQUESTED_LOCK = threading.Lock()


def enabled() -> bool:
    return os.environ.get("EXVIUS_CLIENT_REPORTS") == "1"


def _folder() -> str:
    import data_paths
    base = os.environ.get("FFBE_DATA") or getattr(data_paths, "DATA_ROOT", None) or "."
    folder = os.path.join(base, "client-reports")
    os.makedirs(folder, exist_ok=True)
    return folder


def _save(plaintext) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(_folder(), f"{stamp}-{int(time.time() * 1000) % 1000:03d}.txt")
    text = plaintext if isinstance(plaintext, str) else repr(plaintext)
    # The log itself is usually one string field inside the request; unwrap it so the file is readable.
    pretty = text
    try:
        body = json.JSONDecoder().raw_decode(text)[0]
        pieces = []
        for group, rows in body.items():
            for row in rows if isinstance(rows, list) else [rows]:
                if isinstance(row, dict):
                    for key, value in row.items():
                        pieces.append(f"[{group}.{key}]\n{value}")
        if pieces:
            pretty = "\n\n".join(pieces)
    except (ValueError, AttributeError):
        pass
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(pretty)
        fh.write("\n\n----- raw request -----\n")
        fh.write(text)
    return path


def _profile_id(plaintext) -> str | None:
    try:
        body = json.loads(plaintext or "")
    except (TypeError, ValueError):
        return None
    rows = body.get("LhVz6aD2") if isinstance(body, dict) else None
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("9Tbns0eI") not in (None, ""):
            return str(row["9Tbns0eI"])
    return None


def handle(spec, reply_id, plaintext):
    """Add the report-back request to carrier replies (when on), and answer a log upload (saved when on)."""
    on = enabled()
    if not on:
        with _REQUESTED_LOCK:
            _REQUESTED_PROFILES.clear()
    if reply_id == STORE_LOG_REQUEST:
        size = len(plaintext or "")
        if on:
            path = _save(plaintext or "")
            print(f"CLIENT REPORT: game uploaded its log ({size} chars) -> {path}", flush=True)
        else:
            print(f"CLIENT REPORT: game uploaded a queued log ({size} chars); not saved "
                  f"(EXVIUS_CLIENT_REPORTS=0)", flush=True)
        return {REPORT_STATE_GROUP: [{REPORT_STATE_VALUE: "0"}]}
    if not on:
        return spec
    if reply_id in CARRIERS and isinstance(spec, dict):
        profile_id = _profile_id(plaintext)
        if profile_id is None:
            return spec
        with _REQUESTED_LOCK:
            if profile_id in _REQUESTED_PROFILES:
                return spec
            _REQUESTED_PROFILES.add(profile_id)
        spec = dict(spec)
        # A time in the past: upload as soon as the report scheduler next runs.
        spec[REPORT_BACK_GROUP] = [{REPORT_BACK_TIME: "2020-01-01 00:00:00", REPORT_BACK_HOLD: "0"}]
    return spec
