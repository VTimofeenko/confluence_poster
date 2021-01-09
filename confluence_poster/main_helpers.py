from atlassian import Confluence
from dataclasses import dataclass, field
from typing import Union, Callable, List
from typer import echo, prompt, confirm
from functools import partial

from confluence_poster.poster_config import Page, Config

"""File that contains procedures used inside main.py's functions"""


def get_page_url(
    page_title: str, space: str, confluence: Confluence
) -> Union[str, None]:
    """Retrieves page URL"""
    if page := confluence.get_page_by_title(space=space, title=page_title, expand=""):
        # according to Atlassian REST API reference, '_links' is a legitimate way to access links
        page_link = confluence.url + page["_links"]["webui"]
        return page_link
    else:
        return None


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
    page_id: Union[int, None] = None


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
    _filter_mode: bool = False
    quiet: bool = False

    @property
    def print_function(self) -> Callable:
        if self.quiet:
            # noinspection PyUnusedLocal
            def _quiet_func(*args, **kwargs):
                pass

            return _quiet_func
        else:
            return echo

    @property
    def always_print_function(self) -> Callable:
        return echo

    @property
    def prompt_function(self) -> Callable:
        if self.filter_mode:
            # noinspection PyUnusedLocal
            def _raise_exception(*args, **kwargs):
                raise Exception("Prompt invoked in filter mode!")

            return _raise_exception
        else:
            return prompt

    @property
    def confirm_function(self) -> Callable:
        if self.filter_mode:
            # noinspection PyUnusedLocal
            def _raise_exception(*args, **kwargs):
                # TODO: show prompt?
                raise Exception("Confirmation prompt invoked in filter mode!")

            return _raise_exception
        else:
            return confirm

    @property
    def print_stderr(self) -> Callable:
        return partial(echo, err=True)

    @property
    def filter_mode(self):
        return self._filter_mode

    @filter_mode.setter
    def filter_mode(self, value: bool):
        self._filter_mode = value
        if value:
            self.quiet = True
