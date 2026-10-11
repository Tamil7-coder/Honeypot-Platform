"""
Dionaea -> Platform log shipper (HTTP + FTP + SMB).

Dionaea (https://github.com/DinoTools/dionaea) emulates several vulnerable
network services from a single process -- httpd, ftpd, smbd, mysqld,
mssqld, tftpd, sip, upnpd -- primarily to capture malware that
self-propagates by exploiting them. Its `log_json` ihandler writes one JSON
object per line to a log file, one line per "incident" (connection
accepted, request received, file downloaded, shellcode profiled...).

This shipper is single-process/single-honeypot, matching how the real
Dionaea engine works: one `dionaea-01` Honeypot entity, with `protocol`
distinguishing HTTP/FTP/SMB sessions the same way cowrie-shipper already
distinguishes SSH/Telnet from a single Cowrie instance. (An earlier version
of this shipper registered a separate "dionaea-http-01" honeypot; that was
an HTTP-only oversight, corrected here now that FTP/SMB are wired up too.)

Per the project's honeypot-to-protocol mapping, Dionaea covers HTTP, FTP,
and SMB. DNS/RDP/MQTT/MySQL/MSSQL/PostgreSQL are handled by a separate
OpenCanary shipper, SMTP by Mailoney, and ICS/Modbus by Conpot.

--- Schema (per Dionaea's official log_json ihandler docs) ---
https://dionaea.readthedocs.io/en/latest/ihandler/log_json.html documents
the wire format as a NESTED object:

    {
      "connection": {
        "protocol": "httpd" | "ftpd" | "smbd" | ...,
        "type": "accepted" | "listen" | ...,
        "transport": "tcp" | "udp",
        "remote": {"address": "...", "port": 1234, "hostname": "..."},
        "local":  {"address": "...", "port": 80}
      }
    }

log_json is explicitly documented as "pre alpha" and some Dionaea builds/
forks add extra top-level keys alongside "connection" for richer incidents
(e.g. command/credential capture). This shipper reads the nested
"connection" object as the authoritative source for protocol/host/port
(required for every incident), and *additionally* looks for a set of
plausible flat/legacy field names for the optional richer fields (HTTP
method+path, FTP user/pass, SMB shellcode profile) so it degrades
gracefully -- a build that only emits bare connection events still gets
correctly attributed HTTP/FTP/SMB sessions, and a build that emits more
still gets the extra detail.

--- Log path resolution ---
docker-compose.yml now mounts the `dionaea_logs` volume directly onto
Dionaea's real state directory (/opt/dionaea/var/lib/dionaea) on both the
`dionaea` and `dionaea-shipper` services, and enables the log_json
ihandler via a bind-mounted config (dionaea-config/ihandlers-enabled/
log_json.yaml) that writes to file://@DIONAEA_STATEDIR@/dionaea.json. So
under the shipped compose file the log always lands at exactly
/dionaea-logs/dionaea.json. DIONAEA_LOG_PATH_CANDIDATES is still
overridable (comma-separated) in case of a custom Dionaea layout.
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

API_URL = os.getenv("INGEST_API_URL", "http://backend:8000/api/v1/attacks/ingest")
HONEYPOT_NAME = os.getenv("HONEYPOT_NAME", "dionaea-01")
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "2"))
SESSION_IDLE_TIMEOUT_SECONDS = float(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", "5"))

_DEFAULT_LOG_PATH_CANDIDATES = [
    "/dionaea-logs/dionaea.json",
    "/dionaea-logs/log/dionaea.json",
    "/dionaea-logs/dionaea/dionaea.json",
    "/dionaea-logs/bistream/dionaea.json",
]
_LOG_PATH_CANDIDATES = (
    os.getenv("DIONAEA_LOG_PATH_CANDIDATES", "").split(",")
    if os.getenv("DIONAEA_LOG_PATH_CANDIDATES")
    else _DEFAULT_LOG_PATH_CANDIDATES
)

# Dionaea's connection_protocol values -> our normalized protocol name.
_PROTOCOL_MAP = {"httpd": "http", "ftpd": "ftp", "smbd": "smb"}

# session bucket key -> {protocol, commands, files, meta, last_seen}
_sessions: dict[str, dict] = defaultdict(
    lambda: {"commands": [], "files": [], "login_attempts": [], "meta": {}, "last_seen": 0.0}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_log_path() -> str:
    """Polls candidate paths until one exists, logging progress so a
    misconfigured/unexpected Dionaea layout is diagnosable from the
    container logs rather than failing silently."""
    print(f"[dionaea-shipper] Searching for Dionaea log among: {_LOG_PATH_CANDIDATES}")
    while True:
        for candidate in _LOG_PATH_CANDIDATES:
            candidate = candidate.strip()
            if candidate and os.path.exists(candidate):
                print(f"[dionaea-shipper] Found log file at: {candidate}")
                return candidate
        print("[dionaea-shipper] No candidate log path exists yet, waiting for Dionaea to start logging...")
        time.sleep(POLL_INTERVAL_SECONDS)


def _parse_timestamp(event: dict) -> str:
    ts = event.get("connection_timestamp") or event.get("timestamp")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    if isinstance(ts, str):
        try:
            parsed = datetime.fromisoformat(ts)
        except ValueError:
            return _now_iso()
        if parsed.tzinfo is None:
            # Dionaea's log_json timestamps have no timezone suffix but are
            # in UTC (the container's own clock). Without this, the naive
            # datetime crashes the backend's duration calculation when it's
            # subtracted against an offset-aware datetime elsewhere.
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    return _now_iso()


def _extract_connection_fields(event: dict) -> dict | None:
    """Fields common to every Dionaea connection incident, regardless of
    which emulated protocol handled it.

    Reads the documented nested `connection` object first
    (connection.remote.address / connection.remote.port /
    connection.local.port); falls back to legacy/flat field names for
    forks that don't nest the data.
    """
    conn = event.get("connection")
    if isinstance(conn, dict):
        remote = conn.get("remote") or {}
        local = conn.get("local") or {}
        remote_host = remote.get("address")
        remote_port = remote.get("port")
        local_port = local.get("port")
    else:
        remote_host = None
        remote_port = None
        local_port = None

    # Legacy/flat fallback (older forks, or custom submit_http payloads).
    remote_host = remote_host or event.get("remote_host") or event.get("src_ip")
    remote_port = remote_port if remote_port is not None else event.get("remote_port")
    local_port = local_port if local_port is not None else event.get("local_port")

    if not remote_host:
        return None
    return {
        "remote_host": remote_host,
        "remote_port": remote_port,
        "local_port": local_port,
        "timestamp": _parse_timestamp(event),
    }


def _extract_http(event: dict, conn: dict) -> dict:
    method = event.get("http_method") or event.get("method")
    path = event.get("http_url") or event.get("url") or event.get("path")
    user_agent = event.get("http_user_agent") or event.get("user_agent")
    headers = event.get("http_headers") or event.get("headers")

    command_text = f"{method or 'GET'} {path}" if (method or path) else f"HTTP connection from {conn['remote_host']}"
    metadata = {k: v for k, v in {"method": method, "path": path, "user_agent": user_agent, "headers": headers}.items() if v}
    return {"command_text": command_text, "command_metadata": metadata or None}


def _extract_ftp(event: dict, conn: dict) -> dict:
    ftp_command = event.get("ftp_command") or event.get("command")
    ftp_args = event.get("ftp_command_arg") or event.get("args")
    username = event.get("ftp_user") or event.get("username")
    password = event.get("ftp_pass") or event.get("password")

    if ftp_command:
        command_text = f"FTP {ftp_command}" + (f" {ftp_args}" if ftp_args else "")
    else:
        command_text = f"FTP connection from {conn['remote_host']}"

    return {
        "command_text": command_text,
        "command_metadata": {"ftp_command": ftp_command, "args": ftp_args} if ftp_command else None,
        "username": username,
        "password": password,
    }


def _extract_smb(event: dict, conn: dict) -> dict:
    # Dionaea's smbd is primarily used to capture exploit attempts
    # (e.g. MS17-010/EternalBlue-style shellcode) rather than file listing
    # commands, so incidents here are more often "shellcode profiled" than
    # a literal SMB verb.
    incident = event.get("incident") or event.get("eventid") or ""
    profile = event.get("profile") or event.get("shellcode_profile")

    if "shellcode" in incident.lower() or profile:
        command_text = "SMB exploit shellcode detected"
        metadata = {"profile": profile} if profile else None
    else:
        command_text = f"SMB connection from {conn['remote_host']}"
        metadata = None

    return {"command_text": command_text, "command_metadata": metadata}


_EXTRACTORS = {"http": _extract_http, "ftp": _extract_ftp, "smb": _extract_smb}


def _handle_line(line: str) -> None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return

    conn_obj = event.get("connection")
    dionaea_protocol = (conn_obj or {}).get("protocol") if isinstance(conn_obj, dict) else None
    dionaea_protocol = dionaea_protocol or event.get("connection_protocol")  # legacy fallback
    protocol = _PROTOCOL_MAP.get(dionaea_protocol)
    if protocol is None:
        return  # not an HTTP/FTP/SMB incident (or a protocol we don't handle here)

    conn = _extract_connection_fields(event)
    if conn is None:
        return

    key = f"{protocol}:{conn['remote_host']}:{conn['remote_port'] or 'unknown'}"
    bucket = _sessions[key]
    bucket["last_seen"] = time.time()
    bucket["protocol"] = protocol

    if not bucket["meta"]:
        bucket["meta"] = {
            "session_ref": f"dionaea-{protocol}-{conn['remote_host']}-{conn['remote_port']}-{int(time.time())}",
            "source_ip": conn["remote_host"],
            "source_port": conn["remote_port"],
            "destination_port": conn["local_port"],
            "protocol": protocol,
            "started_at": conn["timestamp"],
        }

    extracted = _EXTRACTORS[protocol](event, conn)

    username = extracted.get("username")
    password = extracted.get("password")
    md5hash = event.get("md5hash")
    download_url = event.get("url")
    has_file = bool(md5hash or (download_url and protocol in ("http", "ftp")))
    has_creds = bool(username or password)
    is_generic_fallback = extracted["command_text"].endswith(f"connection from {conn['remote_host']}")

    # Skip adding a bare "connection from X" filler command when this same
    # incident already yielded a login attempt or a file record -- those
    # carry the real signal, and a generic line alongside them is noise
    # rather than useful replay-timeline content.
    if not (is_generic_fallback and (has_creds or has_file)):
        bucket["commands"].append(
            {"command_text": extracted["command_text"], "command_metadata": extracted.get("command_metadata")}
        )

    if has_creds:
        bucket["login_attempts"].append({"username": username or "", "password": password or "", "success": False})

    # File downloads (payload staging) can occur over HTTP or FTP.
    if has_file:
        bucket["files"].append(
            {"direction": "download", "url": download_url, "filename": None, "file_size": None, "sha256": md5hash}
        )


def _flush_idle_sessions() -> None:
    now = time.time()
    expired = [key for key, bucket in _sessions.items() if now - bucket["last_seen"] > SESSION_IDLE_TIMEOUT_SECONDS]

    for key in expired:
        bucket = _sessions.pop(key)
        if not bucket["meta"]:
            continue

        payload = {
            "honeypot_name": HONEYPOT_NAME,
            **bucket["meta"],
            "ended_at": _now_iso(),
            "login_attempts": bucket["login_attempts"],
            "commands": bucket["commands"],
            "files": bucket["files"],
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
            if resp.status_code >= 400:
                print(f"[dionaea-shipper] Ingestion failed ({resp.status_code}): {resp.text}")
            else:
                print(
                    f"[dionaea-shipper] Shipped {bucket['protocol'].upper()} session from "
                    f"{bucket['meta']['source_ip']} ({len(bucket['commands'])} event(s))"
                )
        except requests.RequestException as exc:
            print(f"[dionaea-shipper] Error posting session: {exc}")


def tail_log() -> None:
    log_path = _resolve_log_path()
    print(f"[dionaea-shipper] Watching {log_path} (HTTP/FTP/SMB), shipping to {API_URL}")

    with open(log_path, "r") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                _flush_idle_sessions()
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            _handle_line(line)


if __name__ == "__main__":
    tail_log()
