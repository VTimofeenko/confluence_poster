from typer.testing import CliRunner, Result
from confluence_poster.main import app, state
from utils import clone_local_config, mark_online_only, generate_run_cmd
from atlassian import Confluence
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


def test_post_single_page():
    """Test with good default config, to check that everything is OK"""
    result: Result = run_with_config(input="Y\nN\nY\n")
    global created_page_ids
    created_page_ids += state.created_pages
    global working_confluence_instance
    working_confluence_instance = state.confluence_instance

    assert result.exit_code == 0


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
