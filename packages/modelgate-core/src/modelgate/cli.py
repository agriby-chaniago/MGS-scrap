"""Entry point for the `modelgate` command (Fase 4, see ROADMAP.md).

The `check` subcommand's core (parse, audit, --json) was pulled forward
into Fase 3 out of necessity: the conformance corpus (spec §7.3) defines
conformance through a process-level CLI contract —

    <tool> check <fixture-dir> --json

— which can't be exercised without a real `check` command existing.
Fase 4 completes it: `--spec` version pinning (spec §8's requirement
that a caller can pin an exact spec version, and that the tool refuses
rather than silently evaluating against a different one).
"""

import argparse
import sys

from modelgate import audit
from modelgate.manifest import SPEC_VERSION


def _normalize_spec_arg(spec: str) -> str:
    """'mgs-1.0', 'MGS-1.0', '1.0' all mean the same thing to a user."""
    return spec.lower().removeprefix("mgs-").removeprefix("v")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modelgate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Evaluate a Dataset against MGS")
    check_parser.add_argument("path")
    check_parser.add_argument(
        "--json", action="store_true", help="Print the full Report as JSON"
    )
    check_parser.add_argument(
        "--spec",
        default=None,
        metavar="VERSION",
        help=(
            f"Pin the exact MGS spec version to evaluate against (e.g. mgs-1.0). "
            f"This build implements MGS {SPEC_VERSION} only — refuses to run "
            f"rather than silently evaluating against a version you didn't ask "
            f"for (spec §8)."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        if args.spec is not None and _normalize_spec_arg(args.spec) != SPEC_VERSION:
            print(
                f"modelgate: requested spec {args.spec!r}, but this build only "
                f"implements MGS {SPEC_VERSION}. Refusing to run rather than "
                f"silently evaluating against the wrong version — see spec §8.",
                file=sys.stderr,
            )
            return 2

        report = audit(args.path)
        if args.json:
            print(report.to_json())
        else:
            print(f"MGS {report.spec_version} — {report.overall_verdict}")
            for r in report.requirements:
                print(f"  {r.id}: {r.verdict}")
        # Non-zero exit on anything but a clean PASS — required for
        # `modelgate check` to be usable as a CI gate (Fase 4 exit criteria).
        return 0 if report.overall_verdict == "PASS" else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
