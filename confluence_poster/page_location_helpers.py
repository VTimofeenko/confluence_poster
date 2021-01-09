from typing import Union

from confluence_poster.main_helpers import StateConfig, get_page_url
from confluence_poster.poster_config import Page


def _find_parent(parent_name: str, space: str, state: StateConfig) -> Union[int, None]:
    """Helper function to locate the parent page.

    :return page id if parent is found, None otherwise
    """
    state.print_function(f"Looking for the parent page with title '{parent_name}'")
    if parent_page := state.confluence_instance.get_page_by_title(
        space=space, title=parent_name, expand=""
    ):
        # according to Atlassian REST API reference, '_links' is a legitimate way to access links
        parent_link = get_page_url(parent_name, space, state.confluence_instance)
        _parent_id = parent_page["id"]
        state.print_function(
            f"Found page #{_parent_id}, called '{parent_name}'. URL is: {parent_link}"
        )
        return _parent_id
    else:
        state.print_function(f"Parent page '{parent_name}' not found")
        return None


def _prompt_for_parent(state: StateConfig) -> str:
    """Function that handles user input """
    prompt = state.prompt_function
    return prompt("Which page should the script look for?")


class LocationResult:
    def __init__(
        self,
        create_page: bool,
        parent_page_id: Union[int, None] = None,
        parent_page_name: Union[str, None] = None,
    ):
        self.create_page = create_page
        self.parent_page_id = parent_page_id
        self.parent_page_name = parent_page_name

    def __bool__(self):
        return self.create_page


def determine_location(
    page: Page,
    create_in_root: bool,
    state: StateConfig,
) -> LocationResult:
    """Handles user input when creating the page

    :return bool - whether page should be created, page_id of parent page if it exists, None for creating in root
    """
    echo = state.print_function
    confirm = state.confirm_function
    always_echo = state.always_print_function

    if create_in_root:
        echo(f"Will create the page in root of space {page.page_space}")
        return LocationResult(True, None)

    if page.parent_page_title:
        echo(
            f"Will create the page under the specified parent page '{page.parent_page_title}'"
        )
        parent_page_id = _find_parent(
            parent_name=page.parent_page_title, space=page.page_space, state=state
        )
        if parent_page_id is not None:
            return LocationResult(True, parent_page_id, page.parent_page_title)
        else:
            always_echo(
                f"Provided page '{page.parent_page_title}' not found in space '{page.page_space}'.\n"
                "Skipping page."
            )
            return LocationResult(False)

    else:
        while confirm(
            f"Should the script look for a parent in space {page.page_space}?"
            f" (N to be prompted to create the page in the space root)\n"
            f"Hint: you can pass --create-in-space-root or --parent-page-title to skip this prompt."
        ):
            parent_title = _prompt_for_parent(state)
            if parent_id := _find_parent(
                parent_name=parent_title, space=page.page_space, state=state
            ):
                if confirm(
                    f"Proceed to create the page '{page.page_title}' under page '{parent_title}'?"
                ):
                    return LocationResult(True, parent_id, parent_title)
                else:
                    return LocationResult(False)
        else:
            if confirm(
                f"Create the page in the root of space '{page.page_space}'? (N will skip the page)"
            ):
                return LocationResult(True, None)
            else:
                return LocationResult(False)
