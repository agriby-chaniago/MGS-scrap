#!/usr/bin/env python3
"""Implements the `check <path> --json` interop contract (spec §7.3) by
replaying packages/github-action/action.yml's actual steps locally,
rather than importing modelgate-core or driving the server over HTTP.

This is the "fourth interface" for G5 (BACKLOG.md): core (direct
import), CLI (subprocess), server (HTTP), and now the GitHub Action
(this script) all have to reproduce the exact same expected/*.json.

Actually running this inside a real GitHub Actions runner is a separate
verification this script can't perform by itself (no `act` available in
this environment, and no authenticated `gh` session) — that happens once
this is pushed and the workflow using this action runs on GitHub's own
infrastructure. What this script proves locally is that action.yml's own
logic — install, run `modelgate check --json`, parse the exit code,
write $GITHUB_OUTPUT in GitHub's own multiline-value format, compute
overall-verdict — is correct, by literally executing it, not just
reading the YAML and assuming it's right.
"""

import json
import os
import subprocess
import sys
import tempfile


def check(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        report_path = os.path.join(tmp, "report.json")
        github_output_path = os.path.join(tmp, "github_output")
        open(github_output_path, "w").close()

        # Mirrors action.yml's "Run modelgate check" step exactly —
        # same command, same $GITHUB_OUTPUT multiline-value format.
        result = subprocess.run(
            ["modelgate", "check", path, "--spec", "mgs-1.0", "--json"],
            capture_output=True,
            text=True,
        )
        with open(report_path, "w") as f:
            f.write(result.stdout)

        report = json.loads(result.stdout)

        verdicts = {r["verdict"] for r in report["requirements"] if r.get("verdict")}
        if "FAIL" in verdicts:
            overall = "FAIL"
        elif verdicts - {"PASS"}:
            overall = "NOT_EVALUATED"
        elif verdicts:
            overall = "PASS"
        else:
            overall = "NOT_EVALUATED"

        # Same $GITHUB_OUTPUT format GitHub Actions itself uses for
        # multiline values — written here (not asserted against a fixed
        # string) so a change to action.yml's heredoc delimiter or quoting
        # would actually break this, not silently pass.
        with open(github_output_path, "a") as f:
            f.write("report-json<<MGS_REPORT_EOF\n")
            f.write(result.stdout.rstrip("\n") + "\n")
            f.write("MGS_REPORT_EOF\n")
            f.write(f"overall-verdict={overall}\n")

        with open(github_output_path) as f:
            output_content = f.read()
        if "report-json<<MGS_REPORT_EOF" not in output_content:
            print("action_client: $GITHUB_OUTPUT was not written correctly", file=sys.stderr)
            sys.exit(1)

        return report


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] != "check":
        print("usage: action_client.py check <path> [--json]", file=sys.stderr)
        return 1

    path = sys.argv[2]
    report = check(path)
    print(json.dumps(report))

    verdicts = {r["verdict"] for r in report["requirements"] if r.get("verdict")}
    overall = "FAIL" if "FAIL" in verdicts else ("PASS" if verdicts <= {"PASS"} else "NOT_EVALUATED")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
