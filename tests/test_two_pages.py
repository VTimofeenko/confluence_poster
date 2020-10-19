from typer.testing import CliRunner
import pytest
from confluence_poster.main import app
from confluence_poster.poster_config import Page, Config
from utils import generate_run_cmd, generate_local_config, page_created, get_pages_ids_from_stdout,\
    get_page_body, mk_tmp_file, other_user_config, generate_fake_page, confluence_instance, run_with_config
from functools import partial


"""This module requires an instance of confluence running. The tests will be done against it.
 
Tests scenarios involving two pages. Tests with scenarios require a config with a different user, 'other_user_config'"""

pytestmark = pytest.mark.online
runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


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


@pytest.mark.parametrize("force", [False, True])
def test_one_author_correct_other_not(make_two_pages, tmp_path, force):
    """In two page scenario, the config.author changed one page, and somebody else changed the other page.
    If force flag is set, the pages need to be updated. Else - only one page"""
    config_file, config = make_two_pages
    run_with_config(config_file=config_file,
                    input="Y\n"  # create first page
                          "N\n"  # do not look for parent
                          "Y\n"  # create in root
                          "Y\n"  # create second page
                          "N\n"
                          "Y\n")
    # Update one of the pages with a new author. Requires a separate config for a different user
    page = config.pages[1]
    *_, new_page_file = generate_fake_page(tmp_path)
    other_author_config_file = mk_tmp_file(tmp_path, filename="other_author.toml",
                                           config_to_clone=other_user_config,
                                           key_to_update="pages.page1", value_to_update={
                                                                                            'page_name': page.page_name,
                                                                                            'page_file': new_page_file,
                                                                                        })
    result = run_with_config(config_file=other_author_config_file,
                             pre_args=['--force'])
    assert result.exit_code == 0

    # Now the original user edits the two original pages
    for page_no in range(1):
        *_, new_page_file = generate_fake_page(tmp_path)
        config_file = mk_tmp_file(tmp_path, config_to_clone=config_file,
                                  key_to_update=f"pages.page{page_no+1}.page_file",
                                  value_to_update=new_page_file)
    config = Config(config_file)  # need to reload config

    if force:
        result = run_with_config(config_file=config_file,
                                 pre_args=['--force'])
        assert result.exit_code == 0
        assert result.stdout.count("Updating page") == 2
        # Check that all pages are updated
        config = Config(config_file)  # need to reload config here
        for page in config.pages:
            page_id = confluence_instance.get_page_by_title(space=page.page_space, title=page.page_name)['id']
            with open(page.page_file, 'r') as f:
                page_content = f.read()
                assert page_content in get_page_body(page_id)
    else:
        result = run_with_config(config_file=config_file)
        assert result.exit_code == 0
        assert result.stdout.count("Updating page") == 1
        # Check that first page is updated
        page = config.pages[0]
        page_id = confluence_instance.get_page_by_title(space=page.page_space, title=page.page_name)['id']
        with open(page.page_file, 'r') as f:
            page_content = f.read()
            assert page_content in get_page_body(page_id)

        # Check that second page is not
        page = config.pages[1]
        page_id = confluence_instance.get_page_by_title(space=page.page_space, title=page.page_name)['id']
        with open(page.page_file, 'r') as f:
            page_content = f.read()
            assert page_content not in get_page_body(page_id)


def test_one_page_parent_of_other(make_two_pages):
    """Tests the scenario of two pages, one is the parent of another"""
    config_file, config = make_two_pages
    parent_page: Page
    child_page: Page
    parent_page, child_page = config.pages[0], config.pages[1]
    result = run_with_config(config_file=config_file,
                             input="Y\n"  # create first page
                                   "N\n"  # do not look for parent
                                   "Y\n"  # create in root
                                   "Y\n"  # create second page
                                   "Y\n"  # look for parent
                                   f"{parent_page.page_name}\n"  # page name
                                   "Y\n")
    assert result.exit_code == 0
    child_page_id = confluence_instance.get_page_id(space=parent_page.page_space, title=child_page.page_name)
    parent_page_id = confluence_instance.get_page_id(space=parent_page.page_space, title=parent_page.page_name)
    assert confluence_instance.get_parent_content_id(child_page_id) == parent_page_id
    assert all([_ in get_pages_ids_from_stdout(result.stdout) for _ in [child_page_id, parent_page_id]])


def test_update_both_pages(make_two_pages, tmp_path):
    """Checks that both pages will be updated if required"""
    config_file, config = make_two_pages
    run_with_config(config_file=config_file,
                    input="Y\n"  # create first page
                          "N\n"  # do not look for parent
                          "Y\n"  # create in root
                          "Y\n"  # create second page
                          "N\n"
                          "Y\n")
    for page_no in range(1):  # TODO: DRY?
        *_, new_page_file = generate_fake_page(tmp_path)
        config_file = mk_tmp_file(tmp_path, config_to_clone=config_file,
                                  key_to_update=f"pages.page{page_no+1}.page_file",
                                  value_to_update=new_page_file)
    config = Config(config_file)  # need to reload config
    result = run_with_config(config_file=config_file)
    assert result.exit_code == 0
    assert result.stdout.count("Updating page") == 2
    for page in config.pages:
        page_id = confluence_instance.get_page_by_title(space=page.page_space, title=page.page_name)['id']
        with open(page.page_file, 'r') as f:
            page_content = f.read()
            assert page_content in get_page_body(page_id)
