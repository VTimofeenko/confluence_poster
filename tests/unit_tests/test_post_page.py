from typer.testing import CliRunner, Result
from typing import Union
import pytest
from confluence_poster.main import app, state
from utils import clone_local_config, mark_online_only, generate_run_cmd
from atlassian import Confluence, errors
from functools import wraps
from faker import Faker
import re


"""This module requires an instance of confluence running. The tests will be done against it. To skip this module
set 'VALIDATE_ONLINE' environment variable to something other than 'yes'."""

pytestmark = mark_online_only()

runner = CliRunner()
mk_tmp_file = clone_local_config()
run_with_config = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])


def gen_fake_title():
    """Generates a fake page title. Default fixture behavior is to purge .unique which does not work for my tests"""
    f = Faker()
    while True:
        yield f.sentence(nb_words=3)


fake_title_generator = gen_fake_title()


def run_with_title(page_title: str = None,  fake_title=True, *args, **kwargs,):
    """Helper function to create pages with specific title. Generates fake title by default"""
    if page_title is None and fake_title:
        page_title = next(fake_title_generator)
    else:
        raise ValueError("Fake title is False and no real title was provided")

    page_title = "Py test: " + page_title

    return run_with_config(pre_args=['--page-name', page_title], *args, **kwargs), page_title


def get_page_id_from_stdout(stdout: str) -> Union[int, None]:
    """Function to parse stdout and get the created page id"""
    if result := re.findall("Created page #[0-9]+", stdout):
        return result[0].split("#")[1]
    else:
        return None


# To store created pages for the teardown
created_page_ids = set()
# To actually do the teardown
working_confluence_instance: Confluence


def record_state(f):  # TODO: maybe dynamic teardown is better?
    """Decorator to record the created pages in the test's internal list after the test is run"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(*args, **kwargs)
        global created_page_ids
        created_page_ids.update(state.created_pages)
        global working_confluence_instance
        working_confluence_instance = state.confluence_instance

    return wrapper


def check_created_pages(f):  # TODO: spams the API with unneeded gets
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
def test_page_overridden_title():
    """Tests that the title supplied through command line is applied"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "Y\n"  # do create in root
                                        )
    assert result.exit_code == 0
    assert state.confluence_instance.get_page_by_id(state.created_pages[0])['title'] == page_title, \
        "Page title was not applied from command line"


@check_created_pages
@record_state
def test_post_single_page_no_parent():
    """Test with good default config, to check that everything is OK. Creates a sample page in the root of the space"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "Y\n"  # do create in root
                                        )
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert "Page not found" in result.stdout
    assert "Creating page" in result.stdout
    assert "Finished processing pages" in result.stdout

    assert result.exit_code == 0


@pytest.mark.skip
def test_not_create_if_refused():
    page_title = 'Refused page'
    result = run_with_config(input="N\n",  # it should not be created
                             pre_args=['--page-title', page_title])
    assert result.exit_code == 0
    assert 'Not creating page' in result.stdout, "Script did not report that page is not created"
    assert working_confluence_instance.get_page_by_title(space=state.config.pages[0].page_space,
                                                         title=page_title) is None, \
        "Page was not supposed to be created"


@check_created_pages
@record_state
@pytest.fixture(scope='function')
def setup_parent():
    """Creates a page that will be the parent"""
    result, parent_title = run_with_title(input="Y\n"  # create page
                                                "N\n"  # do not look for parent
                                                "Y\n"  # do create in root of the space
                                          )
    assert result.exit_code == 0
    return get_page_id_from_stdout(result.stdout), parent_title


@check_created_pages
@record_state
def test_post_single_page_with_parent(tmp_path, setup_parent):
    # Create the first page, it will be the parent
    parent_id, parent_page_name = setup_parent
    # create the second page, it will be a child
    child_page_name = "Child page name"
    result, _ = run_with_title(input=f"Y\n"  # create page
                                     f"Y\n"  # look for parent
                                     f"{parent_page_name}\n"  # title of the parent
                                     f"Y\n"  # yes, proceed to create
                               )
    assert result.exit_code == 0
    assert "Which page should the script look for?" in result.stdout
    assert "Found page #" in result.stdout
    assert "URL is:" in result.stdout
    assert "Proceed to create?" in result.stdout
    assert get_page_id_from_stdout(result.stdout) in state.confluence_instance.get_child_id_list(parent_id)


@pytest.mark.skip
def test_post_multiple_pages():
    pass


@pytest.mark.skip
def test_post_force_overwrite():
    pass


@pytest.mark.skip
def test_one_author_correct_other_not():
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    The other page needs to be skipped"""
    pass


def teardown_module():
    """Removes the pages that were created during the test"""
    for page_id in created_page_ids:
        try:
            working_confluence_instance.remove_page(page_id=page_id, recursive=True)
        except errors.ApiError as e:
            # Discarding 404-d pages, they were probably already removed
            if e.args[0].startswith("There is no content"):
                pass
            else:
                raise e
