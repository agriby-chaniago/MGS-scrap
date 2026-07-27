#!/usr/bin/env python3
"""Implements the `check <path> --json` interop contract (spec §7.3) by
driving modelgate-server over HTTP instead of importing modelgate-core.

This is what lets `conformance/runner.py --tool "python3 conformance/server_client.py"`
prove G5 (BACKLOG.md) for real: the server's Report — built from Reader +
Storage (MinIO) + Checker (modelgate-core via analysis_service) +
Aggregator (report_service) — has to reproduce the exact same
expected/*.json as modelgate-core evaluated directly. That's a stronger
claim than "the two use the same library", since it also exercises
upload, storage round-tripping (G7), and the whole async pipeline.

Assumes the server stack is already running at $MGS_SERVER_URL (default
http://localhost:8080) with AUTH_REQUIRED=false (the default — see
auth_service/routers/internal.py), so no credentials are needed.
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile

import requests

BASE_URL = "http://localhost:8080"
POLL_INTERVAL_S = 0.5
POLL_TIMEOUT_S = 30


def _request_with_backoff(method: str, url: str, **kwargs) -> requests.Response:
    """Nginx's general_zone rate limit (60r/m, burst=20 — nginx.conf) is
    an intentional abuse guard, not something a real client should treat
    as fatal. A conformance run driving 12 fixtures back-to-back through
    upload+audit+poll+summary trips it easily; a well-behaved client
    backs off and retries rather than failing outright, so this does
    too."""
    for attempt in range(6):
        resp = requests.request(method, url, **kwargs)
        if resp.status_code != 429:
            return resp
        time.sleep(2**attempt * 0.5)  # 0.5, 1, 2, 4, 8, 16s
    return resp


def _zip_directory_in_memory(dir_path: str) -> bytes:
    """The server's upload endpoint only ever accepts a single ZIP file
    (a real HTTP API, unlike a CLI, can't take an arbitrary directory as
    input) — that's a legitimate API design choice, not a gap. To still
    run an ImageFolder fixture through the server for G5 comparison, zip
    it on the fly here, client-side. This isn't cheating the comparison:
    modelgate-core's ZipReader will read the exact same files back out
    on the server side, and dataset_hash is already proven Reader-
    independent (see conformance/fixtures/generate.py's ImageFolder
    fixture matching its ZIP equivalent's hash exactly)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for root, _dirs, files in os.walk(dir_path):
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, dir_path)
                zf.write(full, arcname)
    return buf.getvalue()


def check(path: str) -> dict:
    if os.path.isdir(path):
        file_bytes = _zip_directory_in_memory(path)
    else:
        # Read the whole file into memory up front, not a file handle —
        # a retried request (rate-limit backoff) re-reading an
        # already-EOF'd file handle would silently send an empty body on
        # the second attempt. Small fixtures only (this is a conformance
        # corpus, not meant for multi-gigabyte datasets), so this is fine.
        with open(path, "rb") as f:
            file_bytes = f.read()

    upload_resp = _request_with_backoff(
        "POST",
        f"{BASE_URL}/api/v1/datasets/upload",
        files={"file": (path, file_bytes, "application/zip")},
        data={"name": path},
    )
    upload_resp.raise_for_status()
    dataset_id = upload_resp.json()["data"]["dataset_id"]

    audit_resp = _request_with_backoff(
        "POST",
        f"{BASE_URL}/api/v1/audits",
        json={"dataset_id": dataset_id, "force": True},
    )
    audit_resp.raise_for_status()
    audit_id = audit_resp.json()["data"]["id"]

    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        status_resp = _request_with_backoff("GET", f"{BASE_URL}/api/v1/audits/{audit_id}")
        status_resp.raise_for_status()
        status = status_resp.json()["data"]["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(POLL_INTERVAL_S)
    else:
        raise TimeoutError(f"audit {audit_id} did not finish within {POLL_TIMEOUT_S}s")

    summary_resp = _request_with_backoff("GET", f"{BASE_URL}/api/v1/reports/{audit_id}/summary")
    summary_resp.raise_for_status()
    data = summary_resp.json()["data"]

    # Reshape to match modelgate-core's Report.to_dict() exactly, so
    # runner.py's normalize() (which strips generated_at/tool_version) can
    # compare this against the same expected/*.json used for the core and
    # CLI. tool_version/generated_at are added here only so the shape
    # matches structurally before runner.py strips them right back out.
    return {
        "spec_version": data["spec_version"],
        "tool_version": "modelgate-server",
        "dataset_hash": data["dataset_hash"],
        "generated_at": None,
        "requirements": data["requirements"],
        "informative": data["informative"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("path")
    check_parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "check":
        report = check(args.path)
        print(json.dumps(report))
        overall = None
        verdicts = {r["verdict"] for r in report["requirements"] if r.get("verdict")}
        if "FAIL" in verdicts:
            overall = "FAIL"
        elif verdicts - {"PASS"}:
            overall = "NOT_EVALUATED"
        elif verdicts:
            overall = "PASS"
        return 0 if overall == "PASS" else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
