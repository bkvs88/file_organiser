"""Central logging configuration for the file organiser.

All modules import ``setup_logging`` so that every successful and failed
file operation is recorded in a single log file.

Why logging instead of print()? Logs carry timestamps, levels and file/line
information out of the box, can be redirected to a file, and let you filter
messages by severity (INFO, WARNING, ERROR, ...). This is the standard way to
observe what a command-line tool is doing.
"""

import logging
import os
from pathlib import Path

# The name of the root logger. All other loggers (detection, movement) are
# created as *children* of this logger via getChild().
LOGGER_NAME = "file_organiser"

# Decide where to write the log file.
# os.environ.get("FILE_ORGANISER_LOG", <default>) lets users override the
# location with an environment variable; if none is set we fall back to a
# file_organiser.log sitting next to this source file.
# Path(__file__).resolve().parent is the directory containing this file
# (resolve() turns relative paths into absolute ones first).
# Path("a.b", "c") style call chains into the default argument produce the
# final path object.
LOG_FILE = Path(
    os.environ.get(
        "FILE_ORGANISER_LOG",
        Path(__file__).resolve().parent / "file_organiser.log",
    )
)

# The layout written for every log record:
#   asctime   -> human-readable timestamp of the event
#   levelname -> INFO / WARNING / ERROR / ...
#   filename  -> the source file producing the message
#   lineno    -> the line number in that file (great for debugging)
#   name      -> the logger that emitted it (e.g. file_organiser.detection)
#   message   -> the actual message
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(name)s - %(message)s"

# The timestamp format matched against the %(asctime)s field above.
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file=None):
    """Configure the shared 'file_organiser' logger and return it.

    Re-runnable: calling this again swaps the current handler for a new one,
    which is used by the tests to redirect logs to a temporary file.
    """
    # logging.getLogger() returns the *same* logger object every time it is
    # called with the same name, so all modules share one logger.
    logger = logging.getLogger(LOGGER_NAME)

    # Set the minimum severity level. Records below INFO (e.g. DEBUG) are
    # simply discarded by this logger.
    logger.setLevel(logging.INFO)

    # A "handler" is the sink that writes log records somewhere (here: a file).
    # Before adding a new handler we remove and close old ones. This makes the
    # function re-runnable: repeated calls do not stack duplicate handlers,
    # which is exactly what the tests rely on to switch log files.
    # We iterate over a copy (logger.handlers[:]) because removing items from
    # a list while iterating over it would skip entries.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # If the caller passed an explicit log_file (a Path or string) use it,
    # otherwise fall back to the module-level LOG_FILE constant above.
    file_path = Path(log_file) if log_file else LOG_FILE

    # Create a handler that appends log records to the file (creating it if
    # it does not exist yet).
    handler = logging.FileHandler(file_path)

    # A formatter controls how each record is turned into text; we reuse the
    # shared FORMAT strings from the top of this module so the format stays
    # consistent across the whole application.
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # Attach the handler to the logger so records actually get written.
    logger.addHandler(handler)

    # By default, a record emitted by "file_organiser.detection" also bubbles
    # up to the root logger and could be printed twice. Setting propagate to
    # False stops that doubling; only our handler handles the record.
    logger.propagate = False

    # Hand the configured logger back to the caller so it can create child
    # loggers (e.g. logger.getChild("detection")).
    return logger