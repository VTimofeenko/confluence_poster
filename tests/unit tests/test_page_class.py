from pathlib import Path
from marshmallow import ValidationError
from dataclasses import asdict
import pytest

from confluence_poster.poster_config import (
    Page,
    PageSchema,
    AllowedFileFormat,
    AllowedFileFormatField,
)

pytestmark = pytest.mark.offline


@pytest.mark.parametrize(
    "file_format",
    ["confluencewiki", "markdown", "html", "None"],
    ids=lambda f_format: f"'{f_format}' is specified for the page",
)
def test_file_format_supported(file_format):
    file_format = AllowedFileFormat(file_format)
    p = Page(
        page_title="Title",
        page_file="/tmp/file.confluencewiki",
        page_space="LOC",
        page_file_format=file_format,
    )
    assert p.page_file_format == file_format
    PageSchema().load(asdict(p))


def test_file_format_default():
    p = Page(
        page_title="Title",
        page_file="/tmp/file.confluencewiki",
        page_space="LOC",
    )
    assert p.page_file_format.value is "None"


def test_file_format_not_str():
    with pytest.raises(ValidationError):
        # noinspection PyTypeChecker
        _ = Page(
            page_title="Title",
            page_file="/tmp/file.confluencewiki",
            page_space="LOC",
            page_file_format=1,
        )
        PageSchema().load(asdict(_))


def test_file_format_different_str():
    with pytest.raises(ValidationError):
        # noinspection PyTypeChecker
        _ = Page(
            page_title="Title",
            page_file="/tmp/file.confluencewiki",
            page_space="LOC",
            page_file_format="not supported",
        )
        PageSchema().load(asdict(_))


@pytest.mark.parametrize(
    "file_exists", [True, False], ids=["Page file exists", "Page file does not exist"]
)
def test_page_text(tmp_path, file_exists):
    content = "h1. Test\nColorless green ideas"
    updated_content = content + " sleep furiously"

    if file_exists:
        page_file: Path = tmp_path / "page.confluencewiki"
        page_file.write_text(content)
    else:
        page_file = tmp_path / "none.md"

    p = Page(page_title="title", page_file=str(page_file), page_space="LOC")

    if file_exists:
        assert p.page_text == content

    p.page_text = updated_content
    assert p.page_text == updated_content
