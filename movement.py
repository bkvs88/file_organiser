"""File movement logic, including duplicate and permission handling.

This module performs the actual work of moving a file from its current
location into an organised `target_root/<category>` folder. It validates
everything up front (does the file exist? is the destination usable? would we
overwrite a file?) and converts low-level OS errors into the custom exceptions
defined in exceptions.py. Every step is logged so operations can be audited.
"""

# shutil provides high-level file operations. shutil.move() either renames the
# file (same filesystem) or copies+deletes it (across filesystems), which is
# exactly the behaviour we want — it works everywhere.
import shutil

# pathlib.Path gives a clean, object-oriented way to build paths with " / "
# and to inspect files. It is preferred over os.path string concatenation.
from pathlib import Path

# Import the custom exceptions we raise from this module. Multi-line import
# in parentheses keeps the line count sane and is the standard PEP 8 style.
from exceptions import (
    DestinationError,
    DuplicateFileError,
    FileNotExistError,
    PermissionDeniedError,
)

# Import the logging setup to share the application-wide log file.
from logging_config import setup_logging

# Child logger so log lines say "file_organiser.movement" in the output,
# making it easy to filter where a message came from.
logger = setup_logging().getChild("movement")


def ensure_destination(folder):
    """Create the destination folder on disk. Raise on permission errors.

    Returns the folder as a Path object so callers can use it in further
    path operations without re-parsing the string.
    """
    # Normalise the folder argument into a Path object.
    folder_path = Path(folder)

    # try/except: attempt the operation, handle known failure modes cleanly.
    try:
        # mkdir creates the directory.
        # parents=True also creates any missing parent directories
        #   (e.g. creating "a/b/c" creates "a" and "a/b" too).
        # exist_ok=True means "do not error if it already exists".
        folder_path.mkdir(parents=True, exist_ok=True)

    # PermissionError is a built-in exception raised by the OS when the
    # process lacks read/write access to the location.
    except PermissionError:
        # Record the failure in the log for the operator.
        logger.error("Permission denied creating destination folder: %s", folder)
        # Re-raise as our custom exception. "from None" hides the original
        # traceback (the PermissionError), keeping the error message clean
        # while still labelling the problem precisely.
        raise PermissionDeniedError(folder) from None

    # Extra safety check: even though mkdir should have worked, verify the
    # result is truly a directory (e.g. a file may exist with that name,
    # or the path may point somewhere unexpected).
    if not folder_path.is_dir():
        logger.error("Destination folder is missing or invalid: %s", folder)
        raise DestinationError(folder)

    # Successful setup — log it so operations are auditable.
    logger.info("Destination folder ready: %s", folder_path)

    # Return the Path so callers can append filenames with "/" naturally.
    return folder_path


def move_file(source, target_root, category, overwrite=False):
    """Move a single file into '<target_root>/<category>'.

    Returns the destination path on success. Raises a custom exception for
    missing source files, missing destinations, duplicates and permission
    problems. Every successful or failed operation is written to the log file.

    Arguments:
        source     - path to the file to move (string or Path).
        target_root- root folder under which the category folder is created.
        category   - name of the category folder, e.g. "Images".
        overwrite  - if False (default), refuse when the destination exists;
                     if True, delete the existing destination before moving.
    """
    # Convert the source into a Path object for the checks below.
    source_path = Path(source)

    # Guard rail #1: the source must exist at all.
    # .exists() returns False for missing files AND for broken symlinks.
    if not source_path.exists():
        logger.error("File does not exist: %s", source_path)
        raise FileNotExistError(source_path)

    # Guard rail #2: it must be a regular file, not a directory or a special
    # device. We would not want to "move" a whole directory by accident.
    if not source_path.is_file():
        logger.error("%s is not a regular file", source_path)
        # We reuse FileNotExistError but with a clearer, tailored message
        # (a directory technically exists, but cannot be moved as a file).
        raise FileNotExistError(f"{source_path} is not a regular file")

    # Build '<target_root>/<category>' with "/" (pathlib joins them cleanly)
    # and hand it to ensure_destination, which creates the folder if needed
    # and returns a Path.
    # Path(target_root) wraps the possibly-string target_root.
    category_dir = ensure_destination(Path(target_root) / category)

    # Guard rail #3: if the source file is ALREADY inside the destination
    # folder, moving it is meaningless (and could confuse the move).
    # .parent gives the folder containing the file.
    if category_dir == source_path.parent:
        logger.error("%s is already inside its destination folder", source_path)
        raise DestinationError(f"{source_path} is already inside its destination folder")

    # The full target path: category folder + the source's file name.
    # We keep the original filename (.name) — we never rename the file, only
    # relocate it.
    destination = category_dir / source_path.name

    # Guard rail #4: handle the case where a file already exists at the
    # destination.
    if destination.exists():
        # If overwrite is True, replace the existing destination file.
        if overwrite:
            try:
                # unlink() deletes the existing file so the move below can
                # put the new one in its place.
                destination.unlink()
                logger.warning("Overwriting existing destination: %s", destination)
            except PermissionError:
                logger.error("Cannot overwrite destination: %s", destination)
                raise PermissionDeniedError(f"cannot overwrite {destination}") from None
        # If overwrite is False, this is a collision — refuse loudly so no
        # data is silently clobbered.
        else:
            logger.warning("Duplicate file, refusing to overwrite: %s", destination)
            raise DuplicateFileError(destination)

    # All validations passed — perform the actual move (the "main" step).
    # str(...) converts to plain strings because shutil wants string paths
    # (non-ASCII filenames are handled fine by Path and shutil, but passing
    # strings is the most compatible, well-tested path).
    try:
        shutil.move(str(source_path), str(destination))
    # Permission errors from the OS become our custom exception.
    except PermissionError:
        logger.error("Permission denied moving: %s", source_path)
        raise PermissionDeniedError(source_path) from None
    # shutil.Error covers other move failures, e.g. destination appeared
    # between our check and the move (a race), or a cross-device failure.
    # In practice a collision here is reported as a duplicate.
    except shutil.Error as exc:
        logger.error("Failed to move %s -> %s (%s)", source_path, destination, exc)
        raise DuplicateFileError(f"{source_path} -> {destination} ({exc})") from None

    # Log the successful outcome, including the category for readability.
    logger.info("Moved '%s' -> '%s' (category '%s')", source, destination, category)

    # Return the destination path so the caller knows where the file landed.
    return destination