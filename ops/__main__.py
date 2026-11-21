"""Backup, restore and portable export of a local Basic Memory store."""

import argparse
import os
from pathlib import Path

from . import backup, export, restore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name, help_text in (
        ("backup", "Back up a live store into a new destination"),
        ("restore", "Restore a backup into a new destination"),
        ("export", "Export every configured project as portable OKF bundles"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("source", type=Path)
        command.add_argument("destination", type=Path)
        if name == "restore":
            command.add_argument(
                "--expected-manifest-digest",
                help="SHA-256 of manifest.json obtained from a trusted source",
            )
    args = parser.parse_args()
    os.umask(0o077)
    if args.operation == "backup":
        backup(args.source, args.destination)
    elif args.operation == "restore":
        restore(args.source, args.destination, expected_manifest_digest=args.expected_manifest_digest)
    else:
        export(args.source, args.destination)
    print(args.destination)


if __name__ == "__main__":
    main()
