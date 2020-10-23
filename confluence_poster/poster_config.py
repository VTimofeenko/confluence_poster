import toml
from dataclasses import dataclass
from typing import Union
from operator import attrgetter
from itertools import groupby


@dataclass
class Page:
    page_title: str
    page_file: str
    page_space: Union[str, None]


@dataclass
class Auth:
    url: str
    username: str
    password: Union[str, None]
    is_cloud: bool = False


class Config(object):
    """Class that loads the config file and provides interface to its values"""
    def __init__(self, file: str):
        _ = toml.load(file)

        self.pages = _["pages"]
        self.auth = _["auth"]
        self.author = _["author"]

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
                    default_space = item_content.get("page_space", None)  # None is OK here, checked later
                    if not isinstance(default_space, str) or default_space is None:
                        raise ValueError("default.page_space should be a string")
                else:  # this is a page definition
                    for prop in item_content:
                        if not isinstance(item_content[prop], str):
                            raise ValueError(f"{prop} property of a page is not a string")

                    page = Page(item_content.get('page_title', None),
                                item_content['page_file'],
                                item_content.get('page_space', None))
                    self.__pages.append(page)
            else:
                raise ValueError("Pages section is malformed, refer to sample config.toml")

        # Validate pages
        # Page space may be none, in that case default space must be specified
        # Page name may be none, but the pages list may contain only one. In that case,
        # page title is expected in the main script
        for page in self.__pages:
            if page.page_space is None:
                if default_space is not None:
                    page.page_space = default_space
                else:
                    raise ValueError(f"Page '{page.page_title}' does not have page_space specified,"
                                     f" neither is default space")
            if page.page_title is None and len(self.__pages) > 1:
                raise ValueError("There are more than 1 page, and one of the names is not specified")

            # Check that there are no pages with same space and name - they will overwrite each other
            page_title_func = attrgetter('page_title')
            page_space_func = attrgetter('page_space')
            groups = groupby(sorted(self.__pages, key=page_title_func), page_title_func)
            for page_title, g in groups:
                _ = list(g)
                groups_space = groupby(sorted(_, key=page_space_func), page_space_func)
                for space_name, group in groups_space:
                    _ = list(group)
                    if len(_) > 1:
                        raise ValueError(f"There are more than 1 page called '{page_title}' in space {space_name}")

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, auth: dict):
        for mandatory_config in ["confluence_url", "username", "is_cloud"]:
            if mandatory_config not in auth:
                raise KeyError(f"{mandatory_config} not in auth section")
        self.__auth = Auth(auth['confluence_url'], auth['username'], auth.get('password', None), auth['is_cloud'])

    @property
    def author(self):
        return self.__author

    @author.setter
    def author(self, author: str):
        if not isinstance(author, str):
            raise ValueError("Author is not a string")
        self.__author = author
