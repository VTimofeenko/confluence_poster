from atlassian import Confluence
from dataclasses import dataclass, field
from confluence_poster.poster_config import Page, AllowedFileFormat, Config
from typing import Union, Callable, List
from pathlib import Path
from enum import Enum
from typer import echo

"""File that contains procedures used inside main.py's functions"""


def check_last_updated_by(
    page_id: int, username_to_check: str, confluence_instance: Confluence
) -> (bool, str):
    """Checks which user last updated `page_id`. If it's not `username_to_check` — return False
    :param page_id: ID of the page to check
    :param username_to_check: compare this username against the one that last updated the page
    :param confluence_instance: instance of Confluence to run the check
    """
    page_last_updated_by = confluence_instance.get_page_by_id(
        page_id, expand="version"
    )["version"]["by"]
    if confluence_instance.api_version == "cloud":
        page_last_updated_by = page_last_updated_by["email"]  # pragma: no cover
    else:
        page_last_updated_by = page_last_updated_by["username"]

    return page_last_updated_by == username_to_check, page_last_updated_by


@dataclass
class PostedPage(Page):
    """Merges independently set fields with the runtime-set fields"""

    version_comment: Union[str, None] = None


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
        raise ValueError("Posting direct markdown is not supported")
    elif file_format == AllowedFileFormat.html:
        return Representation.editor
    elif file_format == AllowedFileFormat.confluencewiki:
        return Representation.wiki
    else:
        raise ValueError(
            f"Could not determine representation value for {file_format}. This is probably a bug."
        )


@dataclass
class StateConfig:
    """Holds the shared state between typer commands"""

    force: bool = False
    debug: bool = False
    confluence_instance: Union[None, Confluence] = None
    config: Union[None, Config] = None
    minor_edit: bool = False
    print_report: bool = False
    force_create: bool = False
    created_pages: List[int] = field(default_factory=list)
    print_function: Callable = echo


# noinspection PyUnusedLocal
def suppressed_echo(*args, **kwargs):
    """To be used if quiet is passed"""
    pass
