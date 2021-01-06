import toml
from pathlib import Path
from dataclasses import dataclass
from typing import Union
from operator import attrgetter
from itertools import groupby
from collections import UserDict
from marshmallow import Schema, fields, ValidationError
from enum import Enum


class AllowedFileFormat(str, Enum):
    confluencewiki = "confluencewiki"
    markdown = "markdown"
    html = "html"
    none = "None"


@dataclass
class Page:
    page_title: str
    page_file: str
    page_space: Union[str, None]
    parent_page_title: Union[str, None] = None
    _page_text: str = ""

    def __eq__(self, other) -> bool:
        if not isinstance(other, Page):
            raise ValueError
        return (self.page_title == other.page_title) and (
            self.page_space == other.page_space
        )

    @property
    def page_text(self) -> str:
        if self._page_text == "":
            if (_file := Path(self.page_file)).exists():
                self._page_text = Path(self.page_file).read_text()
        return self._page_text

    @page_text.setter
    def page_text(self, value: str):
        self._page_text = value

    page_file_format: AllowedFileFormat = AllowedFileFormat.none
    force_overwrite: Union[bool, None] = False


class AllowedFileFormatField(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, AllowedFileFormat):
            raise ValidationError(f"Invalid value for field: {value}")
        return value.value


class PageSchema(Schema):
    page_title = fields.Str()
    page_file = fields.Str()
    page_space = fields.Str()
    parent_page_title = fields.Str(missing=None)
    _page_text = fields.Str()
    page_file_format = AllowedFileFormatField(
        default=AllowedFileFormat.none, missing=AllowedFileFormat.none
    )
    force_overwrite = fields.Boolean(default=False)


@dataclass
class Auth:
    url: str
    username: str
    password: Union[str, None]
    is_cloud: bool = False


class PartialConfig(UserDict):
    """A class that allows reading file contents or data from a dictionary"""

    def __init__(
        self, file: Union[str, Path, None] = None, data: Union[dict, None] = None
    ):
        if file is None and data is None:
            raise ValueError("No data provided")

        if file is not None and data is not None:
            raise ValueError(
                "Both file and data were provided, cannot determine preference"
            )

        if data is not None:
            _data = data
        else:
            _data = toml.load(file)

        super(PartialConfig, self).__init__(_data)


class Config(PartialConfig):
    """Class that loads the config file and provides interface to its values"""

    def __init__(
        self, file: Union[str, Path, None] = None, data: Union[dict, None] = None
    ):
        """File: file to read config from
        is_global: allows suppressing checks to implement config inheritance"""
        super(Config, self).__init__(file, data)

        _ = self.data
        self.pages = _["pages"]
        self.auth = _["auth"]
        self.author = _.get("author", None)

    @property
    def pages(self):
        return self.__pages

    @pages.setter
    def pages(self, pages: dict):
        self.__pages = list()
        default_space = None
        for item in pages:
            item_content = pages[item]
            if isinstance(item_content, dict):
                if item == "default":
                    default_space = item_content.get(
                        "page_space", None
                    )  # None is OK here, checked later
                    if not isinstance(default_space, str) or default_space is None:
                        raise ValueError("default.page_space should be a string")
                else:  # this is a page definition
                    for prop in item_content:  # TODO: better validation
                        if not isinstance(item_content[prop], str):
                            if prop != "force_overwrite":
                                raise ValueError(
                                    f"{prop} property of a page is not a string"
                                )

                    page = Page(
                        page_title=item_content.get("page_title", None),
                        page_file=item_content["page_file"],
                        page_file_format=AllowedFileFormat(
                            item_content.get("page_file_format", "None")
                        ),
                        page_space=item_content.get("page_space", None),
                        parent_page_title=item_content.get("page_parent_title", None),
                        force_overwrite=item_content.get("force_overwrite", False),
                    )
                    self.__pages.append(page)
            else:
                raise ValueError(
                    "Pages section is malformed, refer to sample config.toml"
                )

        # Validate pages
        # Page space may be none, in that case default space must be specified
        # Page name may be none, but the pages list may contain only one. In that case,
        # page title is expected in the main script
        for page in self.__pages:
            if page.page_space is None:
                if default_space is not None:
                    page.page_space = default_space
                else:
                    raise ValueError(
                        f"Page '{page.page_title}' does not have page_space specified,"
                        f" neither is default space"
                    )
            if page.page_title is None and len(self.__pages) > 1:
                raise ValueError(
                    "There are more than 1 page, and one of the names is not specified"
                )

            # Check that there are no pages with same space and name - they will overwrite each other
            page_title_func = attrgetter("page_title")
            page_space_func = attrgetter("page_space")
            groups = groupby(sorted(self.__pages, key=page_title_func), page_title_func)
            for page_title, g in groups:
                _ = list(g)
                groups_space = groupby(sorted(_, key=page_space_func), page_space_func)
                for space_name, group in groups_space:
                    _ = list(group)
                    if len(_) > 1:
                        raise ValueError(
                            f"There are more than 1 page called '{page_title}' in space {space_name}"
                        )

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, auth: dict):
        for mandatory_config in ["confluence_url", "username", "is_cloud"]:
            if mandatory_config not in auth:
                raise KeyError(f"{mandatory_config} not in auth section")
        self.__auth = Auth(
            auth["confluence_url"],
            auth["username"],
            auth.get("password", None),
            auth["is_cloud"],
        )

    @property
    def author(self):
        return self.__author

    @author.setter
    def author(self, author: Union[str, None]):
        if author is None:
            author = self.auth.username
        if not isinstance(author, str):
            raise ValueError("Author is not a string")
        elif len(author) == 0:
            raise ValueError(
                "Author's name is specified in the config but is empty. "
                "Specify it or remove the setting to use the authentication username for checks."
            )

        self.__author = author
