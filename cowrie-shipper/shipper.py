"""
Cowrie -> Platform log shipper.

Tails Cowrie's cowrie.json log file, groups events by session id, and posts
normalized AttackSessionIngest payloads to the backend ingestion endpoint
once a session closes. Designed to run as its own lightweight container.
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

API_URL = os.getenv("INGEST_API_URL", "http://backend:8000/api/v1/attacks/ingest")
LOG_PATH = os.getenv("COWRIE_LOG_PATH", "/cowrie-logs/cowrie.json")
HONEYPOT_NAME = os.getenv("HONEYPOT_NAME", "cowrie-01")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "2"))

_sessions: dict[str, dict] = defaultdict(
    lambda: {"login_attempts": [], "commands": [], "files": [], "meta": {}}
)


def _parse_ts(ts: str) -> str:
    return ts  # Cowrie emits ISO8601 already; pass through for the API to validate


def _handle_event(event: dict) -> None:
    session_id = event.get("session")
    if not session_id:
        return

    bucket = _sessions[session_id]
    eventid = event.get("eventid", "")

    if eventid == "cowrie.session.connect":
        bucket["meta"] = {
            "session_ref": session_id,
            "source_ip": event.get("src_ip"),
            "source_port": event.get("src_port"),
            "destination_port": event.get("dst_port"),
            "protocol": "telnet" if event.get("protocol") == "telnet" else "ssh",
            "started_at": _parse_ts(event.get("timestamp")),
        }
    elif eventid == "cowrie.login.success":
        bucket["login_attempts"].append(
            {"username": event.get("username", ""), "password": event.get("password", ""), "success": True}
        )
    elif eventid == "cowrie.login.failed":
        bucket["login_attempts"].append(
            {"username": event.get("username", ""), "password": event.get("password", ""), "success": False}
        )
    elif eventid == "cowrie.command.input":
        bucket["commands"].append({"command_text": event.get("input", "")})
    elif eventid == "cowrie.session.file_download":
        bucket["files"].append(
            {
                "direction": "download",
                "url": event.get("url"),
                "filename": event.get("outfile") or event.get("destfile"),
                "file_size": None,
                "sha256": event.get("shasum"),
            }
        )
    elif eventid == "cowrie.session.file_upload":
        bucket["files"].append(
            {
                "direction": "upload",
                "url": None,
                "filename": event.get("filename"),
                "file_size": event.get("size"),
                "sha256": event.get("shasum"),
            }
        )
    elif eventid == "cowrie.session.closed":
        bucket["meta"]["ended_at"] = _parse_ts(event.get("timestamp"))
        _flush_session(session_id)


def _flush_session(session_id: str) -> None:
    bucket = _sessions.pop(session_id, None)
    if not bucket or not bucket["meta"].get("source_ip"):
        return

    payload = {
        "honeypot_name": HONEYPOT_NAME,
        **bucket["meta"],
        "login_attempts": bucket["login_attempts"],
        "commands": bucket["commands"],
        "files": bucket["files"],
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=10)
        if resp.status_code >= 400:
            print(f"[shipper] Ingestion failed ({resp.status_code}): {resp.text}")
        else:
            print(f"[shipper] Shipped session {session_id} from {payload['source_ip']}")
    except requests.RequestException as exc:
        print(f"[shipper] Error posting session {session_id}: {exc}")


def tail_log() -> None:
    print(f"[shipper] Watching {LOG_PATH}, shipping to {API_URL}")
    while not os.path.exists(LOG_PATH):
        print("[shipper] Waiting for cowrie log file to appear...")
        time.sleep(POLL_INTERVAL_SECONDS)

    with open(LOG_PATH, "r") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            _handle_event(event)


if __name__ == "__main__":
    tail_log()
