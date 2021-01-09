from typing import Union

from confluence_poster.main_helpers import StateConfig
from confluence_poster.convert_utils import get_representation_for_format
from confluence_poster.page_location_helpers import determine_location
from confluence_poster.poster_config import Page


class CreationResult:
    def __init__(
        self,
        page_created: bool,
        page_id: Union[int, None] = None,
        comment: Union[str, None] = None,
    ):
        self.page_created = page_created
        self.page_id = page_id
        self.comment = comment

    def __bool__(self):
        return self.page_created


def create_page(page: Page, state: StateConfig, create_in_root: bool) -> CreationResult:
    """Handles user input for page creation.

    :return CreationResult that contains info on whether the page was created and its ID
    """
    echo = state.print_function
    confirm = state.confirm_function

    if state.force_create or confirm("Should the page be created?", default=True):
        if location := determine_location(
            page=page, create_in_root=create_in_root, state=state
        ):
            echo("Creating page...")
            page_id = state.confluence_instance.create_page(
                space=page.page_space,
                title=page.page_title,
                body=page.page_text,
                parent_id=location.parent_page_id,
                representation=get_representation_for_format(
                    page.page_file_format
                ).value,
            )["id"]
            if location.parent_page_id is None:
                page_location_msg = f"in root of the space '{page.page_space}'"
            else:
                page_location_msg = f"under page #{location.parent_page_id}, '{location.parent_page_name}'"

            echo(
                f"Created page #{page_id} {page_location_msg} called '{page.page_title}'."
            )
            return CreationResult(True, page_id)
        else:
            return CreationResult(
                False, comment="Could not determine location for the page."
            )
    else:
        return CreationResult(False, comment="User cancelled creation when prompted.")
