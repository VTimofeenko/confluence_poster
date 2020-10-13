from typer.testing import CliRunner, Result
from confluence_poster.main import app, state
from utils import clone_local_config, mark_online_only, generate_run_cmd
from atlassian import Confluence
from functools import wraps
"""This module requires an instance of confluence running. The tests will be done against it. To skip this module
set 'VALIDATE_ONLINE' environment variable to something other than 'yes'."""

pytestmark = mark_online_only()

runner = CliRunner()
mk_tmp_file = clone_local_config()
run_with_config = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])

# To store created pages for the teardown
created_page_ids = []
# To actually do the teardown
working_confluence_instance: Confluence


def record_state(f):
    """Decorator to record the created pages in the test's internal list after the test is run"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(*args, **kwargs)
        global created_page_ids
        created_page_ids += state.created_pages
        global working_confluence_instance
        working_confluence_instance = state.confluence_instance
    return wrapper


def check_created_pages(f):
    """Decorator to check that the pages that were created in the test actually exist"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(*args, **kwargs)
        for page_id in state.created_pages:
            assert working_confluence_instance.get_page_by_id(page_id=page_id) is not None, \
                f"Page #{page_id} was not created properly and cannot be retrieved from the confluence"
    return wrapper


@check_created_pages
@record_state
def test_post_single_page_no_parent():
    """Test with good default config, to check that everything is OK. Creates a sample page in the root of the space"""
    result: Result = run_with_config(input="Y\nN\nY\n")
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert "Page not found" in result.stdout
    assert "Creating page" in result.stdout
    assert "Finished processing pages" in result.stdout

    assert result.exit_code == 0


def test_post_single_page_with_parent():
    pass


def test_post_multiple_pages():
    pass


def test_post_force_overwrite():
    pass


def test_one_author_correct_other_not():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be skipped"""
    pass


def teardown_module():
    """Removes the pages that were created during the test"""
    for page_id in created_page_ids:
        working_confluence_instance.remove_page(page_id=page_id)
