from enum import Enum
from pathlib import Path
from atlassian import Confluence
from requests import Response
from markdown import markdown

from confluence_poster.poster_config import AllowedFileFormat


def post_to_convert_api(confluence: Confluence, text: str) -> str:
    url = "rest/tinymce/1/markdownxhtmlconverter"
    # the endpoint returns plain text, need to redefine the default header
    headers = {"Content-Type": "application/json"}
    # Keep until https://github.com/atlassian-api/atlassian-python-api/pull/684 is released
    original_advanced_mode = confluence.advanced_mode
    if confluence.advanced_mode is False or confluence.advanced_mode is None:
        confluence.advanced_mode = True

    response: Response = confluence.post(url, data={"wiki": text}, headers=headers)
    # No way to trigger failure for this during tests
    response.raise_for_status()  # pragma: no cover

    confluence.advanced_mode = original_advanced_mode

    return response.text


def convert_using_markdown_lib(text: str) -> str:
    return markdown(text, extensions=("tables", "fenced_code"))


def guess_file_format(page_file: str) -> AllowedFileFormat:
    """Attempts to guess the file format from the page file by the file extension.
    If the extension is unknown raises an error"""
    md_file_formats = {
        ".markdown",
        ".mdown",
        ".mkdn",
        ".md",
        ".mkd",
        ".mdwn",
        ".mdtxt",
        ".mdtext",
        ".text",
        ".Rmd",
    }
    cw_file_formats = {".confluencewiki", ".wiki"}
    html_file_formats = {".html"}
    if (suffix := Path(page_file).suffix) in md_file_formats:
        return AllowedFileFormat.markdown
    elif suffix in cw_file_formats:
        return AllowedFileFormat.confluencewiki
    elif suffix in html_file_formats:
        return AllowedFileFormat.html
    else:
        raise ValueError(f"File format of file {page_file} could not be guessed.")


class Representation(Enum):
    wiki = "wiki"
    editor = "editor"


def get_representation_for_format(file_format: AllowedFileFormat) -> Representation:
    if file_format == AllowedFileFormat.markdown:
        return Representation.editor
    elif file_format == AllowedFileFormat.html:
        return Representation.editor
    elif file_format == AllowedFileFormat.confluencewiki:
        return Representation.wiki
    else:
        raise ValueError(
            f"Could not determine representation value for {file_format}. This is probably a bug."
        )
