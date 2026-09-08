"""Tests for the file organiser modules.

This file follows the pytest convention: test classes group related tests,
each test_* method is one independent check, and plain assert statements do
the verification (pytest reports assertion failures with friendly diffs).
The tests are runnable with just:  pytest
"""

import pytest

# pytest is imported so we can use pytest.raises(...) as a context manager
# to assert that a call raises a specific exception type.
# (pytest is NOT a stdlib module — it comes from the pytest package.)

# Import every custom exception we expect the code to raise. Grouping the
# import, PEP 8 style.
from exceptions import (
    DestinationError,
    DuplicateFileError,
    FileNotExistError,
    FileOrganizerError,
    PermissionDeniedError,
    UnsupportedFileError,
)

# Import the detection helpers under test. EXTENSION_MAP is imported so tests
# loop over the real configuration (keeping the tests in sync with any new
# extensions added to the map).
from detection import (
    EXTENSION_MAP,
    get_category,
    get_extension,
    is_supported,
    list_files,
)

# Import the logging setup so tests can redirect logs to temp files.
from logging_config import setup_logging

# Import the movement functions under test.
from movement import ensure_destination, move_file


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class TestExceptions:
    # Each method below is a tiny, focused test. Methods that only test
    # string formatting and attribute storage are quick and clear enough to
    # be written in a few lines each.

    # Tests the base exception class: message, attribute, inheritance.
    def test_file_organizer_error_base(self):
        # Create an instance of the base error with a message.
        err = FileOrganizerError("base error")
        # str(err) uses Exception.__str__, which returns the message we passed.
        assert str(err) == "base error"
        # The custom attribute set in __init__ must be preserved.
        assert err.message == "base error"
        # It should behave like a normal Python exception.
        assert isinstance(err, Exception)

    # Tests that UnsupportedFileError embeds filename + extension in the message.
    def test_unsupported_file_error(self):
        err = UnsupportedFileError("test.xyz", ".xyz")
        # f-string formatting should place the filename in the message.
        assert "test.xyz" in str(err)
        # ...and the extension too.
        assert ".xyz" in str(err)
        # The saved attributes must match what we passed in.
        assert err.filename == "test.xyz"
        assert err.extension == ".xyz"

    # Edge case: when there is no extension, the message should say 'none'.
    def test_unsupported_file_error_none_extension(self):
        err = UnsupportedFileError("noext", None)
        # "None or 'none'" -> the fallback text must appear in the message.
        assert "none" in str(err)

    # Tests the FileNotExistError message and stored path.
    def test_file_not_exist_error(self):
        err = FileNotExistError("/tmp/missing.txt")
        assert "missing.txt" in str(err)
        assert err.path == "/tmp/missing.txt"

    # Tests the DestinationError message and stored path.
    def test_destination_error(self):
        err = DestinationError("/bad/path")
        assert "bad/path" in str(err)
        assert err.path == "/bad/path"

    # Tests the DuplicateFileError message and stored path.
    def test_duplicate_file_error(self):
        err = DuplicateFileError("/dest/file.txt")
        assert "file.txt" in str(err)
        assert err.path == "/dest/file.txt"

    # Tests the PermissionDeniedError message and stored path.
    def test_permission_denied_error(self):
        err = PermissionDeniedError("/restricted")
        assert "restricted" in str(err)
        assert err.path == "/restricted"

    # Verifies the whole custom hierarchy derives from the one base class,
    # so code can catch FileOrganizerError and still handle every subtype.
    def test_inheritance_chain(self):
        # Loop over each concrete exception class.
        for exc_cls in (
            UnsupportedFileError,
            FileNotExistError,
            DestinationError,
            DuplicateFileError,
            PermissionDeniedError,
        ):
            # issubclass(A, B) checks whether A inherits from B.
            assert issubclass(exc_cls, FileOrganizerError)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
class TestDetection:
    # Tests extension extraction: base name, case-insensitivity, no-ext case.
    def test_get_extension_basic(self):
        # Lowercased suffix should be returned.
        assert get_extension("photo.jpg") == ".jpg"
        # Upper-case extensions are lowercased before returning.
        assert get_extension("doc.PDF") == ".pdf"
        # A name with no dot has no suffix -> empty string.
        assert get_extension("noext") == ""

    # Edge case: leading dot = hidden file -> no extension value.
    def test_get_extension_hidden_file(self):
        assert get_extension(".gitignore") == ""

    # --- The next tests each verify every extension in a category maps back
    # --- to that category. Because they loop over EXTENSION_MAP, adding a new
    # --- extension later automatically gets tested without editing the tests.
    def test_get_category_images(self):
        for ext in EXTENSION_MAP["Images"]:
            # "file<ext>" is just a dummy filename carrying that extension.
            assert get_category(f"file{ext}") == "Images"

    def test_get_category_text(self):
        for ext in EXTENSION_MAP["Text"]:
            assert get_category(f"file{ext}") == "Text"

    def test_get_category_documents(self):
        for ext in EXTENSION_MAP["Documents"]:
            assert get_category(f"file{ext}") == "Documents"

    def test_get_category_data(self):
        for ext in EXTENSION_MAP["Data"]:
            assert get_category(f"file{ext}") == "Data"

    def test_get_category_audio(self):
        for ext in EXTENSION_MAP["Audio"]:
            assert get_category(f"file{ext}") == "Audio"

    def test_get_category_video(self):
        for ext in EXTENSION_MAP["Video"]:
            assert get_category(f"file{ext}") == "Video"

    def test_get_category_archives(self):
        for ext in EXTENSION_MAP["Archives"]:
            assert get_category(f"file{ext}") == "Archives"

    def test_get_category_code(self):
        for ext in EXTENSION_MAP["Code"]:
            assert get_category(f"file{ext}") == "Code"

    def test_get_category_executables(self):
        for ext in EXTENSION_MAP["Executables"]:
            assert get_category(f"file{ext}") == "Executables"

    # Unknown extensions must raise UnsupportedFileError (not return garbage).
    def test_get_category_unsupported(self):
        # pytest.raises(ExcType) is a context manager: the block inside must
        # raise that exception or the test fails. The exception object is
        # captured in exc_info for further assertions.
        with pytest.raises(UnsupportedFileError) as exc_info:
            get_category("file.xyz")
        # exc_info.value is the raised exception; check its message content.
        assert ".xyz" in str(exc_info.value)

    # True cases for is_supported.
    def test_is_supported_true(self):
        assert is_supported("photo.png") is True
        assert is_supported("data.csv") is True

    # False case for is_supported.
    def test_is_supported_false(self):
        assert is_supported("file.xyz") is False

    # tmp_path is a pytest fixture: a fresh, empty, temporary directory that
    # is unique per test and cleaned up automatically. Perfect for filesystem
    # tests — no cleanup code needed.
    def test_list_files(self, tmp_path):
        # Write two visible files: "/" joins paths and write_text creates the
        # file with that content.
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.png").write_text("b")
        # Write one hidden file (name starts with a dot)...
        (tmp_path / ".hidden").write_text("h")
        # ...and create a sub-directory (not a file).
        sub = tmp_path / "subdir"
        sub.mkdir()

        # Call the function under test.
        files = list_files(str(tmp_path))
        # Use a set comprehension to extract just the names for easy checks.
        names = {f.name for f in files}

        # Both visible files must be listed...
        assert "a.txt" in names
        assert "b.png" in names
        # ...the hidden file must NOT be listed...
        assert ".hidden" not in names
        # ...and directories must NOT be listed either.
        assert "subdir" not in names

    # Empty directory -> empty result list.
    def test_list_files_empty_dir(self, tmp_path):
        assert list_files(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------
class TestMovement:
    # ensure_destination should create a brand-new folder.
    def test_ensure_destination_creates_folder(self, tmp_path):
        # Build a path that does not exist yet.
        target = tmp_path / "new_folder"
        # ensure_destination creates it and returns a Path...
        result = ensure_destination(target)
        # ...which must actually be a directory on disk.
        assert result.is_dir()

    # ensure_destination should be fine with an already-existing folder
    # (because exist_ok=True) and not raise or delete anything.
    def test_ensure_destination_existing_folder(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()            # create it beforehand
        result = ensure_destination(target)
        assert result.is_dir()    # still a directory afterwards

    # Happy path: a file is moved from src into dest/Images.
    def test_move_file_basic(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()                        # make the source folder
        dest_root = tmp_path / "dest"          # destination root will be built
        src_file = src_dir / "photo.jpg"
        src_file.write_text("image data")      # create the file to move

        # Perform the move.
        result = move_file(str(src_file), str(dest_root), "Images")

        # The returned path must exist on disk...
        assert result.exists()
        # ...and be inside the "Images" category folder.
        assert result.parent.name == "Images"
        # The original source must now be gone (the move consumed it).
        assert not src_file.exists()

    # Moving a non-existent source raises FileNotExistError.
    def test_move_file_missing_source(self, tmp_path):
        with pytest.raises(FileNotExistError):
            move_file(str(tmp_path / "nonexistent.txt"), str(tmp_path), "Text")

    # A destination collision must be refused when overwrite is False.
    def test_move_file_duplicate_no_overwrite(self, tmp_path):
        # Create the source file.
        src = tmp_path / "file.txt"
        src.write_text("content")
        # Pre-create a destination category folder containing a twin file.
        dest_root = tmp_path / "dest"
        dest_root.mkdir()
        cat_dir = dest_root / "Text"
        cat_dir.mkdir()
        (cat_dir / "file.txt").write_text("existing")

        # Same name at the destination -> DuplicateFileError expected.
        with pytest.raises(DuplicateFileError):
            move_file(str(src), str(dest_root), "Text")

    # With overwrite=True the old destination file is replaced.
    def test_move_file_duplicate_with_overwrite(self, tmp_path):
        # New source content...
        src = tmp_path / "file.txt"
        src.write_text("new content")
        # ...colliding with an existing destination file.
        dest_root = tmp_path / "dest"
        dest_root.mkdir()
        cat_dir = dest_root / "Text"
        cat_dir.mkdir()
        (cat_dir / "file.txt").write_text("old content")

        # overwrite=True must replace the old file with the new one.
        result = move_file(str(src), str(dest_root), "Text", overwrite=True)
        # The destination now holds the new content, not the old...
        assert result.read_text() == "new content"
        # ...and the source no longer exists.
        assert not src.exists()

    # The organiser accepts an explicit category even for unknown extensions
    # when the caller dictates the folder (movement does not classify).
    def test_move_file_unknown_extension(self, tmp_path):
        src = tmp_path / "weird.xyz"
        src.write_text("data")
        # Caller passes category directly -> no classification needed.
        result = move_file(str(src), str(tmp_path), "Unknown")
        assert result.exists()
        assert result.parent.name == "Unknown"

    # Moving a file that already lives in its destination folder is refused.
    def test_move_file_already_in_destination(self, tmp_path):
        # Build dest/Images and place the file straight inside it.
        dest = tmp_path / "dest" / "Images"
        dest.mkdir(parents=True)
        src = dest / "pic.jpg"
        src.write_text("data")

        # Attempting to "move" it into the same folder raises DestinationError.
        with pytest.raises(DestinationError):
            move_file(str(src), str(tmp_path / "dest"), "Images")

    # Category folder is created automatically if missing.
    def test_move_file_creates_category_folder(self, tmp_path):
        src = tmp_path / "song.mp3"
        src.write_text("audio")
        dest = tmp_path / "organized"        # does not exist yet

        # move_file builds "organized/Audio" on the fly.
        result = move_file(str(src), str(dest), "Audio")
        assert result.exists()
        assert result.parent.name == "Audio"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class TestLogging:
    # These tests redirect logging to a temporary file via setup_logging()
    # (remember: setup_logging is re-runnable and swaps its handler), then run
    # a real operation and assert the text shows up in the log file.

    # A successful move must be recorded in the log.
    def test_successful_move_is_logged(self, tmp_path):
        log_file = tmp_path / "operations.log"
        # Re-point the logger at our temp file.
        setup_logging(log_file)

        # Set up a real move scenario.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src = src_dir / "photo.jpg"
        src.write_text("image data")
        dest = tmp_path / "dest"

        # Perform the move (this is what should produce the log line).
        move_file(str(src), str(dest), "Images")

        # The temp log file should now exist and contain the words we expect.
        assert log_file.exists()
        content = log_file.read_text()
        assert "Moved" in content
        assert "Images" in content

    # A failed move (missing source) must also leave an error trace in the log.
    def test_failed_move_is_logged(self, tmp_path):
        log_file = tmp_path / "operations.log"
        setup_logging(log_file)

        # Trigger the failure. pytest.raises confirms the exception type while
        # the code inside still runs (and writes its log line first).
        with pytest.raises(FileNotExistError):
            move_file(str(tmp_path / "missing.txt"), str(tmp_path), "Text")

        # The error message from movement.py must be written to the log.
        assert log_file.exists()
        content = log_file.read_text()
        assert "File does not exist" in content

    # A duplicate refusal must be logged.
    def test_duplicate_is_logged(self, tmp_path):
        log_file = tmp_path / "operations.log"
        setup_logging(log_file)

        # Build a collision between source and destination.
        src = tmp_path / "file.txt"
        src.write_text("content")
        dest_root = tmp_path / "dest"
        dest_root.mkdir()
        cat_dir = dest_root / "Text"
        cat_dir.mkdir()
        (cat_dir / "file.txt").write_text("existing")

        with pytest.raises(DuplicateFileError):
            move_file(str(src), str(dest_root), "Text")

        # The log must mention that a duplicate was detected.
        assert log_file.exists()
        content = log_file.read_text()
        assert "Duplicate file" in content

    # Classification failures (unsupported extension) must also be logged.
    def test_unsupported_classification_is_logged(self, tmp_path):
        log_file = tmp_path / "operations.log"
        setup_logging(log_file)

        # get_category warns AND raises for unknown extensions.
        with pytest.raises(UnsupportedFileError):
            get_category("file.xyz")

        # The WARNING text from detection.py must appear in the log.
        assert log_file.exists()
        content = log_file.read_text()
        assert "Unsupported file type" in content