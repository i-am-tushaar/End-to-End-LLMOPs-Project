"""
Unit Tests for File I/O Utilities
=================================

Purpose:
    Verify that the file I/O utilities correctly handle uploaded files,
    retrieve filenames, read file content, generate safe filenames, and
    save supported files to the target directory.

Functions Tested:
    1. _get_filename(): Retrieves the uploaded file's name.
    2. _read_bytes(): Reads file content as bytes.
    3. _safe_filename(): Generates a safe, unique filename.
    4. save_uploaded_files(): Saves supported files and handles errors.

Testing Approach:
    * Use SimpleNamespace and BytesIO to simulate uploaded files.
    * Use pytest's tmp_path fixture to create temporary test directories.
    * Verify supported and unsupported file extensions.
    * Check error handling when file reading fails.
    * Use parameterized tests to test every supported extension.

Note:
    These tests do not require real uploaded files. Temporary files and
    in memory objects are used to keep the tests isolated and repeatable.
"""

import io
from types import SimpleNamespace

import pytest

from multi_doc_chat.utils.file_io import (
    SUPPORTED_EXTENSIONS,
    _get_filename,
    _read_bytes,
    _safe_filename,
    save_uploaded_files,
)


# ## Tests for _get_filename()


# Test 1: Prefer the filename attribute
# Objective: Verify that the filename attribute takes priority
# over the name attribute when both are available.
def test_get_filename_from_upload_file():
    """Verify that filename takes priority over the name attribute."""

    # Step 1: Create a fake upload with both filename and name.
    uploaded_file = SimpleNamespace(
        filename="report.pdf",
        name="fallback.pdf",
    )

    # Step 2: Verify that filename is returned.
    assert _get_filename(uploaded_file) == "report.pdf"


# Test 2: Fall back to the name attribute
# Objective: Verify that the name attribute is used when
# the filename attribute is unavailable.
def test_get_filename_from_generic_file():
    """Verify that the name attribute is used when filename is unavailable."""

    # Step 1: Create a fake file that only has a name.
    uploaded_file = SimpleNamespace(name="notes.txt")

    # Step 2: Verify that name is returned.
    assert _get_filename(uploaded_file) == "notes.txt"


# Test 3: Use the default filename
# Objective: Verify that "file" is returned when the object
# has neither a filename nor a name attribute.
def test_get_filename_uses_default_name():
    """Verify that 'file' is returned when no filename or name exists."""

    # Step 1: Create a fake file with no name information.
    uploaded_file = SimpleNamespace()

    # Step 2: Verify that the default name is returned.
    assert _get_filename(uploaded_file) == "file"


# ## Tests for _read_bytes()


# Test 4: Read from an upload object
# Objective: Verify that content is read from the file attribute
# of an upload object.
def test_read_bytes_from_upload_file():
    """Verify that content is read from an upload object's file attribute."""

    # Step 1: Create a fake upload that wraps an in memory file.
    uploaded_file = SimpleNamespace(
        file=io.BytesIO(b"PDF content")
    )

    # Step 2: Verify that the bytes are read correctly.
    assert _read_bytes(uploaded_file) == b"PDF content"


# Test 5: Read from a regular file object
# Objective: Verify that content can be read directly
# using the read() method of the object.
def test_read_bytes_from_regular_file_object():
    """Verify that content can be read directly using read()."""

    # Step 1: Create an in memory file object.
    uploaded_file = io.BytesIO(b"Text content")

    # Step 2: Verify that the bytes are read correctly.
    assert _read_bytes(uploaded_file) == b"Text content"


# Test 6: Read from a getbuffer object
# Objective: Verify that memoryview content returned by getbuffer()
# is converted into bytes.
def test_read_bytes_from_getbuffer_object():
    """Verify that memoryview content is converted into bytes."""

    # Step 1: Create a fake file that exposes getbuffer().
    uploaded_file = SimpleNamespace(
        getbuffer=lambda: memoryview(b"Buffer content")
    )

    # Step 2: Call the function being tested.
    result = _read_bytes(uploaded_file)

    # Step 3: Verify the content and that the type is bytes.
    assert result == b"Buffer content"
    assert isinstance(result, bytes)


# Test 7: Reject an unsupported object
# Objective: Verify that an object without a supported reading
# method raises ValueError.
def test_read_bytes_rejects_unsupported_object():
    """Verify that an object without a supported reading method raises ValueError."""

    # Step 1: Pass a plain object and verify that ValueError is raised.
    with pytest.raises(
        ValueError,
        match="Unsupported uploaded file object",
    ):
        _read_bytes(object())


# ## Tests for _safe_filename()


# Test 8: Remove unsafe characters
# Objective: Verify that unsafe characters are replaced
# and the file extension is preserved.
def test_safe_filename_removes_unsafe_characters():
    """Verify that unsafe characters are replaced and the extension is preserved."""

    # Step 1: Generate a safe filename from an unsafe one.
    filename = _safe_filename("My Report!.pdf", ".pdf")

    # Step 2: Verify the extension, the removed characters, and the prefix.
    assert filename.endswith(".pdf")
    assert " " not in filename
    assert "!" not in filename
    assert filename.startswith("my_report_")


# Test 9: Generate unique names
# Objective: Verify that repeated calls with the same filename
# produce different generated names.
def test_safe_filename_generates_unique_names():
    """Verify that repeated filenames produce different generated names."""

    # Step 1: Generate two filenames from the same input.
    first_filename = _safe_filename("report.pdf", ".pdf")
    second_filename = _safe_filename("report.pdf", ".pdf")

    # Step 2: Verify that the generated names are different.
    assert first_filename != second_filename


# ## Tests for save_uploaded_files()


# Test 10: Save every supported extension
# Objective: Verify that every configured file extension
# is accepted and saved with its content.
@pytest.mark.parametrize("extension", sorted(SUPPORTED_EXTENSIONS))
def test_supported_extensions_are_saved(extension, tmp_path):
    """Verify that every configured file extension is accepted and saved."""

    # Step 1: Create a fake upload using the supported extension.
    uploaded_file = SimpleNamespace(
        name=f"sample{extension}",
        read=lambda: b"sample content",
    )

    # Step 2: Save the file into the temporary directory.
    saved_paths = save_uploaded_files([uploaded_file], tmp_path)

    # Step 3: Verify the saved path, extension, and content.
    assert len(saved_paths) == 1
    assert saved_paths[0].suffix == extension
    assert saved_paths[0].read_bytes() == b"sample content"


# Test 11: Skip unsupported extensions
# Objective: Verify that unsupported file types are skipped
# and nothing is written to disk.
def test_unsupported_extension_is_skipped(tmp_path):
    """Verify that unsupported file types are skipped without saving."""

    # Step 1: Create a fake upload with an unsupported extension.
    uploaded_file = SimpleNamespace(
        name="malware.exe",
        read=lambda: b"ignored content",
    )

    # Step 2: Try to save the file.
    saved_paths = save_uploaded_files([uploaded_file], tmp_path)

    # Step 3: Verify that nothing was saved.
    assert saved_paths == []
    assert list(tmp_path.iterdir()) == []


# Test 12: Create the target directory
# Objective: Verify that the destination directory is created
# when it does not exist.
def test_save_uploaded_files_creates_target_directory(tmp_path):
    """Verify that the destination directory is created when it does not exist."""

    # Step 1: Define a target directory that does not exist yet.
    target_dir = tmp_path / "new_folder"

    # Step 2: Create a fake upload with a supported extension.
    uploaded_file = SimpleNamespace(
        name="notes.txt",
        read=lambda: b"Hello world",
    )

    # Step 3: Save the file into the new directory.
    saved_paths = save_uploaded_files([uploaded_file], target_dir)

    # Step 4: Verify that the directory and the file were created.
    assert target_dir.exists()
    assert len(saved_paths) == 1
    assert saved_paths[0].read_bytes() == b"Hello world"


# Test 13: Handle an empty upload list
# Objective: Verify that an empty upload list
# returns an empty list.
def test_save_uploaded_files_with_empty_list(tmp_path):
    """Verify that an empty upload list returns an empty list."""

    # Step 1: Call the function with no uploaded files.
    saved_paths = save_uploaded_files([], tmp_path)

    # Step 2: Verify that an empty list is returned.
    assert saved_paths == []


# Test 14: Wrap file reading errors
# Objective: Verify that errors raised while reading a file
# are wrapped in DocumentPortalException.
def test_save_uploaded_files_wraps_read_errors(tmp_path):
    """Verify that file reading errors are wrapped in DocumentPortalException."""

    # Step 1: Import the custom exception class.
    from multi_doc_chat.exception.custom_exception import DocumentPortalException

    # Step 2: Define a reader that simulates an operating system error.
    def raise_read_error():
        """Simulate an operating system error while reading a file."""
        raise OSError("Simulated file read failure")

    # Step 3: Create a fake upload that fails when read.
    uploaded_file = SimpleNamespace(
        name="notes.txt",
        read=raise_read_error,
    )

    # Step 4: Verify that the error is wrapped in DocumentPortalException.
    with pytest.raises(DocumentPortalException):
        save_uploaded_files([uploaded_file], tmp_path)