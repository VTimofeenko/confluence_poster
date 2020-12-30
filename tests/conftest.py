import pytest
from utils import confluence_instance
from atlassian import errors


@pytest.fixture(scope="session", autouse=True)
def record_pages():
    """Cleans up created pages. The created_pages set is manipulated through inspect module when the runner command
    is executed."""
    created_pages = set()
    yield created_pages

    # Teardown
    for page_id in created_pages:
        try:
            confluence_instance.remove_page(page_id=page_id, recursive=True)
        except errors.ApiError as e:
            # Discarding 404-d pages, they were probably already removed
            if e.args[0].startswith("There is no content"):
                pass
            else:
                raise e
    # check for any py test pages?
