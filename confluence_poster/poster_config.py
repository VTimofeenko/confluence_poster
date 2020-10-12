import toml
from dataclasses import dataclass
from typing import Union


@dataclass
class Page:
    page_name: str
    page_file: str
    page_space: str


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

                    page = Page(item_content['page_name'],
                                item_content['page_file'],
                                item_content.get('page_space', None))
                    self.__pages.append(page)
            else:
                raise ValueError("Pages section is malformed, refer to sample config.toml")

        # Check that all pages have a space
        for page in self.__pages:
            if page.page_space is None:
                if default_space is not None:
                    page.page_space = default_space
                else:
                    raise ValueError(f"Page '{page.page_name}' does not have page_space specified,"
                                     f" neither is default space")

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
