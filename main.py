"""Command-line entry point that organises an entire folder.

This module is the "main" script that combines the two halves of the app:

    detection.py  -> classifies each file into a category ("Images", "Text", ...)
    movement.py   -> physically moves each file into <target_root>/<category>

It ties them together: list the files in the source folder, classify each one,
move it into the right category folder, and finally print/log a summary so the
user knows what happened. It can be run directly:

    python main.py <source_folder> <target_root> [--overwrite]

or imported by other code (pytest, scripts) via organise_folder()/main().
"""

import argparse
import sys
from pathlib import Path

# Detection helpers: list_files finds candidates, get_category classifies.
from detection import get_category, list_files

# Custom exceptions we may need to "catch" and skip a file on, instead of
# letting them crash the whole run.
from exceptions import (
    DestinationError,
    DuplicateFileError,
    FileNotExistError,
    PermissionDeniedError,
    UnsupportedFileError,
)

# Shared logging configuration (all modules write to the same log file).
from logging_config import setup_logging

# Movement: actually performs the move and returns the destination path.
from movement import move_file

# Child logger so messages say "file_organiser.main" in the log output.
logger = setup_logging().getChild("main")


def organise_folder(source, target_root, overwrite=False):
    """Move every supported file from `source` into `target_root/<category>`.

    Returns a summary dict with the counts of each outcome:
        moved        - files successfully moved into a category folder
        unsupported  - files whose extension is not in EXTENSION_MAP
        duplicates   - files refused because the destination already exists
                       (and overwrite is False)
        failed       - files that raised a FileNotExist/Destination/Permission
                       error and could not be moved

    Files that cannot be moved are logged and skipped, never raised: one odd
    file must not abort the organisation of the whole folder.
    """
    # Only regular, non-hidden files in the top level of `source`.
    # (list_files does not recurse into sub-folders.)
    files = list_files(source)

    # Start every counter at zero.
    results = {"moved": 0, "unsupported": 0, "duplicates": 0, "failed": 0}

    # Process each candidate file one at a time.
    for path in files:
        # Step 1 - classification: what category does this file belong to?
        try:
            category = get_category(path.name)

        # Unknown extension: get_category raises UnsupportedFileError (and
        # already logs a warning itself). We just count it and move on.
        except UnsupportedFileError:
            logger.warning("Skipping unsupported file: %s", path)
            results["unsupported"] += 1
            continue  # skip to the next file without moving this one

        # Step 2 - the actual move into '<target_root>/<category>'.
        try:
            move_file(path, target_root, category, overwrite=overwrite)
            results["moved"] += 1

        # The destination already has a file with the same name and overwrite
        # is False: refuse, don't crash.
        except DuplicateFileError as exc:
            logger.warning("Duplicate file, skipping: %s (%s)", path, exc)
            results["duplicates"] += 1

        # Anything else (missing source, bad/permission-restricted destination)
        # is counted as a failure but still does not stop the run.
        except (DestinationError, FileNotExistError, PermissionDeniedError) as exc:
            logger.error("Failed to organise %s (%s)", path, exc)
            results["failed"] += 1

    # Return the tally so callers (CLI or tests) can report it.
    return results


def main(argv=None):
    """Parse command-line arguments and organise the folder.

    Returns the process exit code: 0 on success, 1 if the source folder is
    missing or not a directory.
    """
    # argparse builds a --help text automatically and parses sys.argv.
    parser = argparse.ArgumentParser(
        prog="file_organiser",
        description="Organise a folder's files into category sub-folders.",
    )
    # Positional argument 1: the folder to organise (current dir is default).
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        help="Folder to organise (default: current directory).",
    )
    # Positional argument 2: where the category folders are created.
    parser.add_argument(
        "target_root",
        nargs="?",
        default="organized",
        help="Folder in which category folders are created (default: 'organized').",
    )
    # Flag: allow replacing files that already exist at the destination.
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist at the destination.",
    )
    # Optional: redirect the log file for this run.
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        help="Write logs to PATH instead of the default log file.",
    )
    # argv=None means "use sys.argv[1:]"; passing a list lets tests inject args.
    args = parser.parse_args(argv)

    # If requested, re-point logging BEFORE any work happens. setup_logging is
    # re-runnable and swaps its file handler, so this replaces the default one.
    if args.log_file:
        setup_logging(args.log_file)

    # Guard rail: the source must exist and be a directory.
    source = Path(args.source)
    if not source.is_dir():
        logger.error("Source is not a directory: %s", source)
        print(f"Error: source is not a directory: {source}", file=sys.stderr)
        return 1

    # Announce the run, then do the work.
    logger.info("Organising '%s' into '%s'", args.source, args.target_root)
    results = organise_folder(source, args.target_root, overwrite=args.overwrite)

    # Build a one-line summary for both the log and the console.
    summary = (
        f"Done: {results['moved']} moved, {results['unsupported']} unsupported, "
        f"{results['duplicates']} duplicates, {results['failed']} failed."
    )
    logger.info(summary)
    print(summary)

    # Exit code 0 = successful run.
    return 0


# Standard Python entry point guard: this block only runs when the file is
# executed directly ("python main.py"), NOT when it is imported by pytest or
# another module. sys.exit(main()) passes main's return value to the shell.
if __name__ == "__main__":
    sys.exit(main())