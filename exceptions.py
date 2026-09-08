"""Custom exceptions used across the file organiser.

This module defines a hierarchy of exception classes. Every error raised by the
file organiser inherits from a common base class (``FileOrganizerError``), so
the rest of the program can catch one base type and still know which specific
problem occurred. Learning to read custom exceptions is important for freshers:
they let you attach extra context (like the filename involved) instead of just
a generic message string.
"""


class FileOrganizerError(Exception):
    """Base class for all file organiser errors."""

    # The __init__ method is called automatically when we create an instance
    # of this class, e.g. FileOrganizerError("some message").
    def __init__(self, message):
        # Store the human-readable message on the instance so other code can
        # access it later via `err.message`.
        # str(...) guarantees the message is a string even if a non-string
        # value (e.g. a Path object) was passed in.
        self.message = str(message)
        # super().__init__() calls the base Exception constructor. This sets
        # things up so that str(err) returns the message too, and that the
        # exception works correctly with the Python interpreter (tracebacks,
        # print(), logging, etc.).
        super().__init__(self.message)


class UnsupportedFileError(FileOrganizerError):
    """Raised when a file's extension is not recognized."""

    # The constructor takes the offending filename and its extension so the
    # caller can inspect them after catching the exception.
    def __init__(self, filename, extension):
        # super().__init__() calls FileOrganizerError.__init__, which builds
        # the message string. The two adjacent string literals next to each
        # other are implicit string concatenation: Python joins them into one
        # string. "extension or 'none'" prints 'none' when extension is a
        # falsy value (None or empty string), which is friendlier output.
        super().__init__(
            f"Unsupported file type for '{filename}' "
            f"(extension '{extension or 'none'}')."
        )
        # Save the filename for later programmatic inspection.
        self.filename = filename
        # Save the extension for later programmatic inspection.
        self.extension = extension


class FileNotExistError(FileOrganizerError):
    """Raised when a file that should be moved does not exist."""

    def __init__(self, path):
        # Build the message using an f-string and pass it up to the base class.
        super().__init__(f"File does not exist: {path}")
        # Keep the offending path on the exception object.
        self.path = path


class DestinationError(FileOrganizerError):
    """Raised when the destination folder is missing or cannot be created."""

    def __init__(self, path):
        # An f-string formats the path into a descriptive error message.
        super().__init__(f"Destination folder is missing or invalid: {path}")
        # Save the path that was problematic for later inspection.
        self.path = path


class DuplicateFileError(FileOrganizerError):
    """Raised when a file with the same name already exists at the destination."""

    def __init__(self, path):
        # Build the message describing the conflicting destination path.
        super().__init__(f"Duplicate filename already exists: {path}")
        # Keep the duplicate path on the exception for debugging.
        self.path = path


class PermissionDeniedError(FileOrganizerError):
    """Raised when the program lacks permission to read or write a path."""

    def __init__(self, path):
        # Build the message mentioning the restricted path.
        super().__init__(f"Permission denied: {path}")
        # Keep the restricted path available on the exception.
        self.path = path