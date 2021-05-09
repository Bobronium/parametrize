import sys
from pathlib import Path
from typing import Iterable


TOOLS_DIR = Path(__file__).parent
CHANGELOG = TOOLS_DIR.parent / "changelog.md"


def get_changes(changelog: Iterable[str], expected_version: str = None):
    reading_changes = False

    for line in changelog:
        if line.startswith("## v"):
            if reading_changes:
                break
            reading_changes = True
            if expected_version is None:
                continue

            actual_version = line.split()[1]
            if expected_version != actual_version:
                print(f"Version mismatch: {expected_version=}, {actual_version=}", file=sys.stderr)
                sys.exit(0)
            continue

        print(line.strip())


if __name__ == "__main__":
    with open(CHANGELOG) as changelog_file:
        get_changes(changelog_file, *sys.argv[1:])
