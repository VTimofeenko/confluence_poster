from typer.testing import CliRunner
import pytest
from confluence_poster.main import app
from utils import generate_run_cmd, generate_local_config, page_created, get_pages_ids_from_stdout


"""This module requires an instance of confluence running. The tests will be done against it. To skip this module
set 'VALIDATE_ONLINE' environment variable to something other than 'yes'."""

pytestmark = pytest.mark.online
runner = CliRunner()
run_with_config = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])


@pytest.fixture(scope='function')
def make_two_pages(tmp_path):
    return generate_local_config(tmp_path, pages=2)


def test_post_multiple_pages(make_two_pages, record_pages):
    """Checks that creation of two brand new pages in root of the space works fine"""
    config_file, config = make_two_pages
    result = run_with_config(config=config_file,
                             input="Y\n"  # create first page
                                   "N\n"  # do not look for parent
                                   "Y\n"  # create in root
                                   "Y\n"  # create second page
                                   "N\n"
                                   "Y\n")

    assert result.exit_code == 0
    assert result.stdout.count("Creating page") == 2
    for page in config.pages:
        assert page_created(page.page_name)
    # record created pages
    record_pages |= get_pages_ids_from_stdout(result.stdout)


def test_one_page_refuse_other_posted(make_two_pages, record_pages):
    """In two page case, user rejects creating the second page. Need to check that only one was created"""
    config_file, config = make_two_pages
    result = run_with_config(config=config_file,
                             input="Y\n"  # create first page
                                   "N\n"  # do not look for parent
                                   "Y\n"  # create in root
                                   "N\n")  # do not create the second page
    assert result.exit_code == 0
    assert result.stdout.count("Creating page") == 1
    assert page_created(page_title=config.pages[0].page_name)
    assert not page_created(page_title=config.pages[1].page_name), \
        "The second page should not have been created"
    record_pages |= get_pages_ids_from_stdout(result.stdout)


@pytest.mark.skip
def test_one_author_correct_other_not():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be skipped"""
    raise NotImplemented


@pytest.mark.skip
def test_one_author_correct_other_not_force():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be skipped"""
    raise NotImplemented


@pytest.mark.skip
def test_one_page_parent_of_other():
    raise NotImplemented
