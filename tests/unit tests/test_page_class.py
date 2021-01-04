from confluence_poster.poster_config import Page, PageSchema
from marshmallow import ValidationError
from dataclasses import asdict
import pytest

pytestmark = pytest.mark.offline


@pytest.mark.parametrize(
    "file_format",
    ["confluencewiki", "markdown", "html", None],
    ids=lambda f_format: f"'{f_format}' is specified for the page",
)
def test_file_format_supported(file_format):
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
    assert p.page_file_format is None


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
        _ = Page(
            page_title="Title",
            page_file="/tmp/file.confluencewiki",
            page_space="LOC",
            page_file_format="not supported",
        )
        PageSchema().load(asdict(_))
