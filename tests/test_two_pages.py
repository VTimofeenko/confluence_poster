from typer.testing import CliRunner, Result
import pytest
from confluence_poster.main import app
from confluence_poster.poster_config import Page, Config
from utils import generate_run_cmd, generate_local_config, page_created, get_pages_ids_from_stdout, get_page_title,\
    get_page_body
from inspect import currentframe


"""This module requires an instance of confluence running. The tests will be done against it.
 
Tests scenarios involving two pages"""

pytestmark = pytest.mark.online
runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])


def run_with_config(config_file, *args, **kwargs) -> Result:
    """Function that runs the default_run_cmd with supplied config and records the generated pages in the fixture"""
    result = default_run_cmd(config=config_file, *args, **kwargs)
    # This allows manipulating the set of the pages to be destroyed at the end
    frame = currentframe().f_back.f_back
    record_pages: set = frame.f_locals.get('funcargs')['record_pages']
    assert type(record_pages) is set, "Looks like record_set manipulation is going to fail"
    created_pages = get_pages_ids_from_stdout(result.stdout)
    record_pages |= created_pages
    config = Config(config_file)
    for page_id in created_pages:
        """Make sure that the pages got created with proper content"""
        page_title = get_page_title(page_id)
        found_page: Page = next(_ for _ in config.pages if _.page_name == page_title)
        with open(found_page.page_file, 'r') as page_file:
            page_text = page_file.read()
            assert page_text in get_page_body(page_id), f"Page {page_title} has incorrect content"

    return result


@pytest.fixture(scope='function')
def make_two_pages(tmp_path):
    return generate_local_config(tmp_path, pages=2)


def test_post_multiple_pages(make_two_pages):
    """Checks that creation of two brand new pages in root of the space works fine"""
    config_file, config = make_two_pages
    result = run_with_config(config_file=config_file,
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


def test_one_page_refuse_other_posted(make_two_pages):
    """In two page case, user rejects creating the second page. Need to check that only one was created"""
    config_file, config = make_two_pages
    result = run_with_config(config_file=config_file,
                             input="Y\n"  # create first page
                                   "N\n"  # do not look for parent
                                   "Y\n"  # create in root
                                   "N\n")  # do not create the second page
    assert result.exit_code == 0
    assert result.stdout.count("Creating page") == 1
    assert page_created(page_title=config.pages[0].page_name)
    assert not page_created(page_title=config.pages[1].page_name), \
        "The second page should not have been created"
    # record_pages |= get_pages_ids_from_stdout(result.stdout)


@pytest.mark.skip
def test_one_author_correct_other_not():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be skipped"""
    raise NotImplemented


@pytest.mark.skip
def test_one_author_correct_other_not_force():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be updated"""
    raise NotImplemented


@pytest.mark.skip
def test_one_page_parent_of_other():
    raise NotImplemented


@pytest.mark.skip
def test_update_both_pages():
    raise NotImplemented
