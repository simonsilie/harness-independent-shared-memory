"""Backup, restore and portable export of a local Basic Memory store."""

import os
import sys
from pathlib import Path

import configargparse

from . import backup, export, restore


def main() -> None:
    parser = configargparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name, help_text in (
        ("backup", "Back up a live store into a new destination"),
        ("restore", "Restore a backup into a new destination"),
        ("export", "Export every configured project as portable OKF bundles"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("source", type=Path, nargs="?")
        command.add_argument("destination", type=Path, nargs="?")
        command.add_argument(
            "--source", dest="configured_source", type=Path, metavar="PATH", env_var="SHARED_MEMORY_OPS_SOURCE"
        )
        command.add_argument(
            "--destination",
            dest="configured_destination",
            type=Path,
            metavar="PATH",
            env_var="SHARED_MEMORY_OPS_DESTINATION",
        )
        if name == "restore":
            command.add_argument(
                "--expected-manifest-digest",
                env_var="SHARED_MEMORY_RESTORE_EXPECTED_MANIFEST_DIGEST",
                help="SHA-256 of manifest.json obtained from a trusted source",
            )
    args = parser.parse_args()
    source = args.source or args.configured_source
    destination = args.destination or args.configured_destination
    if source is None or destination is None:
        parser.error("source and destination are required")
    os.umask(0o077)
    if args.operation == "backup":
        backup(source, destination)
    elif args.operation == "restore":
        restore(source, destination, expected_manifest_digest=args.expected_manifest_digest)
    else:
        export(source, destination)
    sys.stdout.write(f"{destination}\n")


if __name__ == "__main__":
    main()
