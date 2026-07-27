"""Entry point for the `modelgate` command.

Minimal `check` subcommand, pulled forward from Fase 4 (see ROADMAP.md)
into Fase 3 out of necessity: the conformance corpus (spec §7.3) defines
conformance through a process-level CLI contract —

    <tool> check <fixture-dir> --json

— rather than by importing implementation internals, and that contract
can't be exercised without a real `check` command existing. This is NOT
the full Fase 4 CLI: no `--spec` version pinning/validation, no PyPI
packaging polish, no other subcommands. Those remain Fase 4 work.
"""

import argparse
import sys

from modelgate import audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modelgate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Evaluate a Dataset against MGS")
    check_parser.add_argument("path")
    check_parser.add_argument(
        "--json", action="store_true", help="Print the full Report as JSON"
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        report = audit(args.path)
        if args.json:
            print(report.to_json())
        else:
            print(f"MGS {report.spec_version} — {report.overall_verdict}")
            for r in report.requirements:
                print(f"  {r.id}: {r.verdict}")
        # Non-zero exit on anything but a clean PASS — a syntactically
        # working exit code is required for `modelgate check` to be
        # usable as a CI gate (Fase 4 exit criteria), and there's no
        # reason to wait until Fase 4 to get this right.
        return 0 if report.overall_verdict == "PASS" else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
