"""File detection and classification by extension.

This module answers two questions about a file:
  1. What is its extension?  -> get_extension()
  2. Which category does it belong to? -> get_category()

The category maps onto the folder the file will be moved into (e.g. all
".jpg" and ".png" files go into an "Images" folder).
"""

# pathlib.Path is the modern, cross-platform way to work with filesystem
# paths. It replaces older os.path string juggling and is more readable.
from pathlib import Path

# Import the custom exception this module raises when it cannot classify a
# file. (Importing directly from "exceptions" works because the modules live
# in the same directory.)
from exceptions import UnsupportedFileError

# Import the logging setup so this module can write into the shared log file.
from logging_config import setup_logging

# Create a child logger named "file_organiser.detection" by calling
# setup_logging() (which builds the shared parent logger) and then getChild().
# Because we call setup_logging() lazily here, any log_file passed by tests
# is already applied by the time this logger is created.
logger = setup_logging().getChild("detection")

# A dictionary mapping a category name (which becomes a folder) to a *set* of
# file extensions belonging to that category.
#
# A set is used instead of a list because set membership checks (the "in"
# operator) are O(1) on average, and here we only ever ask "is this extension
# in this group?", never "in which order are the extensions?".
#
# `.lower()` is applied to all extensions so that lookups match both upper-
# and lower-case files (see get_extension below).
EXTENSION_MAP = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
        ".webp", ".tiff", ".heic",
    },
    "Text": {".txt", ".md", ".log", ".rtf", ".rst"},
    "Documents": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".odt", ".ods"},
    "Data": {".csv", ".json", ".xml", ".yaml", ".yml", ".sql", ".db", ".tsv"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2"},
    "Code": {
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h",
        ".sh", ".go", ".rb", ".html", ".css",
    },
    "Executables": {".exe", ".dmg", ".pkg", ".app", ".bin"},
}


def get_extension(filename):
    """Return the lowercased extension of a file (empty string if none).

    e.g. "photo.JPG" -> ".jpg", "report" -> ""

    Extensions are lowercased so all later category lookups are case-
    insensitive (".JPG" matches ".jpg").
    """
    # Path(filename) wraps the string into a Path object, and .suffix gives
    # the text after the last dot INCLUDING the dot itself (".jpg").
    # .lower() normalises to lower case so lookups are case-insensitive.
    return Path(filename).suffix.lower()


def get_category(filename):
    """Return the category folder for a file, or raise UnsupportedFileError.

    e.g. "my_photo.png" -> "Images", "notes.md" -> "Text"
    """
    # First compute the extension once, and reuse that single value in the
    # loop below (avoids re-parsing the filename repeatedly).
    extension = get_extension(filename)

    # Loop over each (category, extensions) pair in the dictionary.
    # .items() yields ("Images", {".jpg", ...}), ("Text", {".txt", ...}), ...
    for category, extensions in EXTENSION_MAP.items():
        # "in" on a set is a fast membership check; if the file's extension
        # belongs to this category we found the answer.
        if extension in extensions:
            # Return immediately: the first matching category wins.
            return category

    # If we get here, no category contained the extension.
    # Log the failure at WARNING level (visible in the log file, not fatal)
    # so an operator can see which files were skipped and why.
    logger.warning("Unsupported file type: %s (extension '%s')", filename, extension)

    # "raise" stops execution and hands control to the nearest matching
    # except clause upstream. The custom exception also carries the filename
    # and extension for inspection. Passing the filename as an extra info.
    raise UnsupportedFileError(filename, extension)


def is_supported(filename):
    """Return True if the file's extension is recognised."""
    # Try to classify the file...
    try:
        # If get_category() succeeds the extension is supported.
        # We ignore the returned category; we only care about success.
        get_category(filename)
        return True
    # ...and catch the specific exception get_category raises when the
    # extension is unknown.
    except UnsupportedFileError:
        return False


def list_files(folder):
    """Return all regular files in a folder (non-recursive, hidden files ignored).

    Only the top level of `folder` is scanned; sub-folders are not entered.
    """
    # Convert the folder string into a Path object for the operations below.
    folder_path = Path(folder)

    # List comprehension -> builds a list of Path objects.
    # folder_path.iterdir() yields every entry (files AND directories) inside
    # the folder, in arbitrary filesystem order.
    # path.is_file() keeps only regular files, dropping sub-directories.
    # not path.name.startswith(".") filters out hidden files like ".gitignore"
    # (their names begin with a dot).
    return [
        path
        for path in folder_path.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]