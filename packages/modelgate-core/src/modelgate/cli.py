"""Entry point for the `modelgate` command.

Placeholder — the real CLI (`modelgate check ./data --spec mgs-1.0`) is
built in Fase 4 (see ROADMAP.md). Declared as a project.scripts entry
point starting from Fase 1 so the package's public shape does not change
once people start `pip install`-ing it.
"""

import sys


def main() -> int:
    print(
        "modelgate: CLI not yet implemented — this package is in Fase 1 "
        "of its restructuring (see ROADMAP.md). Track progress at "
        "https://github.com/agriby-chaniago/MGS",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
