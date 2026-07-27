#!/usr/bin/env python3
"""Conformance runner — spec §7.2 / §7.3.

Exercises the interop contract (`<tool> check <fixture> --json`) over
every fixture in conformance/fixtures/, comparing against the frozen
expected/*.json. Deliberately invokes the tool as a subprocess, never by
importing modelgate-core directly — the whole point of §7.3 is that a
conformant implementation in ANY language, not just this repo's Python
one, can be pointed at with --tool and pass the exact same corpus.

Usage:
    python3 conformance/runner.py                     # compare against expected/
    python3 conformance/runner.py --update             # (re)freeze expected/ from current output
    python3 conformance/runner.py --tool "some-other-binary"
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(HERE, "fixtures")
EXPECTED_DIR = os.path.join(HERE, "expected")

# Fields that are inherently non-reproducible across runs/machines/tool
# versions, and therefore excluded from comparison (and from the frozen
# expected/*.json) — see spec §4 vs. this runner's own README note below.
_VOLATILE_KEYS = {"generated_at", "tool_version"}


def normalize(report_dict: dict) -> dict:
    return {k: v for k, v in report_dict.items() if k not in _VOLATILE_KEYS}


def run_tool(tool_cmd: list[str], fixture_path: str) -> dict:
    result = subprocess.run(
        [*tool_cmd, "check", fixture_path, "--json"],
        capture_output=True,
        text=True,
    )
    # Exit code is 0 (PASS) or 1 (anything else) per cli.py — both are
    # valid fixture outcomes, not runner errors. Only unparseable stdout
    # (the tool crashed, or doesn't implement --json) is an actual failure.
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"tool produced no valid JSON for {fixture_path}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        ) from e


def diff_summary(expected: dict, actual: dict) -> str:
    lines = []
    exp_reqs = {r["id"]: r for r in expected.get("requirements", [])}
    act_reqs = {r["id"]: r for r in actual.get("requirements", [])}
    for rid in sorted(set(exp_reqs) | set(act_reqs)):
        e, a = exp_reqs.get(rid), act_reqs.get(rid)
        if e != a:
            lines.append(
                f"  {rid}: expected verdict={e and e.get('verdict')!r} "
                f"got verdict={a and a.get('verdict')!r}"
            )
    if expected.get("dataset_hash") != actual.get("dataset_hash"):
        lines.append(
            f"  dataset_hash: expected={expected.get('dataset_hash')} "
            f"got={actual.get('dataset_hash')}"
        )
    return "\n".join(lines) or "  (a field outside requirements/dataset_hash differs)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tool",
        default="modelgate",
        help="Command implementing the check --json contract (spec §7.3). "
        "Space-separated if it needs args, e.g. 'python3 -m modelgate.cli'.",
    )
    parser.add_argument(
        "--update", action="store_true", help="(Re)freeze expected/*.json from current output"
    )
    args = parser.parse_args()
    tool_cmd = args.tool.split()

    os.makedirs(EXPECTED_DIR, exist_ok=True)
    fixture_names = sorted(f for f in os.listdir(FIXTURES_DIR) if f.endswith(".zip"))

    if not fixture_names:
        print("no fixtures found", file=sys.stderr)
        return 1

    failures: list[tuple[str, str]] = []
    for name in fixture_names:
        fixture_path = os.path.join(FIXTURES_DIR, name)
        expected_path = os.path.join(EXPECTED_DIR, name.replace(".zip", ".json"))

        try:
            actual = normalize(run_tool(tool_cmd, fixture_path))
        except RuntimeError as e:
            failures.append((name, str(e)))
            print(f"ERROR    {name}")
            continue

        if args.update or not os.path.exists(expected_path):
            with open(expected_path, "w") as f:
                json.dump(actual, f, indent=2, sort_keys=True)
                f.write("\n")
            print(f"UPDATED  {name}")
            continue

        with open(expected_path) as f:
            expected = json.load(f)

        if actual == expected:
            print(f"OK       {name}")
        else:
            failures.append((name, diff_summary(expected, actual)))
            print(f"MISMATCH {name}")

    if failures:
        print("\n--- failures ---")
        for name, detail in failures:
            print(f"\n{name}:\n{detail}")
        return 1

    print(f"\n{len(fixture_names)} fixtures, all conformant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
