from typer.testing import CliRunner
import pytest
from confluence_poster.main import app, state
from utils import clone_local_config, \
    generate_run_cmd,\
    real_confluence_config,\
    real_config, \
    confluence_instance, \
    mk_fake_file,\
    page_created, fake_title_generator, check_body_and_title, get_page_body, \
    get_pages_ids_from_stdout, \
    get_page_id_from_stdout

from faker import Faker


f"""This module requires an instance of confluence running. 
The tests will be done against it using a {real_confluence_config} 

This is a collection of tests on a single page"""

pytestmark = pytest.mark.online

runner = CliRunner()
mk_tmp_file = clone_local_config()
run_with_config = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])


def run_with_title(page_title: str = None, fake_title=True, *args, **kwargs,):
    """Helper function to create pages with specific title. Generates fake title by default"""
    if page_title is None and fake_title:
        page_title = next(fake_title_generator)
    elif page_title:
        page_title = "Py test: " + page_title
    else:
        raise ValueError("Fake title is False and no real title was provided")

    return run_with_config(pre_args=['--page-name', page_title], *args, **kwargs), page_title


def test_page_overridden_title(record_pages):
    """Tests that the title supplied through command line is applied"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "Y\n"  # do create in root
                                        )
    assert result.exit_code == 0
    assert confluence_instance.get_page_by_id(state.created_pages[0])['title'] == page_title, \
        "Page title was not applied from command line"
    record_pages |= get_pages_ids_from_stdout(result.stdout)


def test_post_single_page_no_parent(record_pages):
    """Test with good default config, to check that everything is OK. Creates a sample page in the root of the space

    Author's note: mirrors setup_page fixture, but kept separately to make failures clearer"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "Y\n"  # do create in root
                                        )
    assert result.exit_code == 0
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert "Page not found" in result.stdout
    assert "Creating page" in result.stdout
    assert "Finished processing pages" in result.stdout

    record_pages |= get_pages_ids_from_stdout(result.stdout)


def test_not_create_if_refused(record_pages):
    page_title = 'Refused page'
    result = run_with_config(input="N\n",  # it should not be created
                             pre_args=['--page-name', page_title])
    assert result.exit_code == 0
    assert 'Not creating page' in result.stdout, "Script did not report that page is not created"
    assert not page_created(page_title=page_title), "Page was not supposed to be created"
    assert len(get_pages_ids_from_stdout(result.stdout)) == 0, "Detected a page that was created!"
    record_pages |= get_pages_ids_from_stdout(result.stdout)


@pytest.fixture(scope='function')
def setup_page(record_pages):
    """Pre-creates a page"""
    result, page_title = run_with_title(input="Y\n"  # create page
                                              "N\n"  # do not look for parent
                                              "Y\n"  # do create in root of the space
                                        )
    assert result.exit_code == 0
    record_pages |= get_pages_ids_from_stdout(result.stdout)
    return get_page_id_from_stdout(result.stdout), page_title


def test_post_single_page_with_parent(setup_page, record_pages):
    # Create the first page, it will be the parent
    parent_id, parent_page_name = setup_page
    # create the second page, it will be a child
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
    assert get_page_id_from_stdout(result.stdout) in confluence_instance.get_child_id_list(parent_id)
    record_pages |= get_pages_ids_from_stdout(result.stdout)


def test_post_force_overwrite_same_author(tmp_path, setup_page, record_pages):
    """Checks that even if force is specified and the author is the same - the page is overwritten.
    If not - it would be silly"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page

    force_result = run_with_config(config=overwrite_config, pre_args=['--force', '--page-name', page_title])
    assert "Updating page" in force_result.stdout
    assert new_text in get_page_body(page_id)
    check_body_and_title(page_id, body_text=new_text, title_text=page_title)
    record_pages |= get_pages_ids_from_stdout(force_result.stdout)


def test_post_force_overwrite_other_author(tmp_path, setup_page, record_pages):
    """Checks that force flag overwrites page if the author is different"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page
    fake_username = Faker().user_name()

    overwrite_config = mk_tmp_file(tmp_path,
                                   config_to_clone=str(overwrite_config),
                                   key_to_update="author", value_to_update=f"Fake: {fake_username}")
    force_result = run_with_config(config=overwrite_config, pre_args=['--force', '--page-name', page_title])
    assert "Updating page" in force_result.stdout
    assert new_text in get_page_body(page_id)
    check_body_and_title(page_id, body_text=new_text, title_text=page_title)
    record_pages |= get_pages_ids_from_stdout(force_result.stdout)


def test_post_no_overwrite_other_author_no_force(tmp_path, setup_page, record_pages):
    """Checks the page is not overwritten if the author is different"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page
    original_username = real_config.author
    fake_username = Faker().user_name()

    overwrite_config = mk_tmp_file(tmp_path,
                                   config_to_clone=str(overwrite_config),
                                   key_to_update="author", value_to_update=f"Fake: {fake_username}")
    overwrite_result = run_with_config(config=overwrite_config, pre_args=['--page-name', page_title])
    assert overwrite_result.exit_code == 0
    assert state.force is not True
    assert "Flag 'force' is not set and last author" in overwrite_result.stdout
    assert original_username in overwrite_result.stdout, \
        "The original username should be mentioned in the script output"
    assert fake_username in overwrite_result.stdout, "The author_to_check username should be mentioned in the script " \
                                                     "output"
    assert new_text not in get_page_body(page_id)
    record_pages |= get_pages_ids_from_stdout(overwrite_result.stdout)


def test_create_and_overwrite_page(tmp_path, setup_page, record_pages):
    """Creates a page and overwrites it"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page

    overwrite_result = run_with_config(config=overwrite_config, pre_args=['--page-name', page_title])
    assert overwrite_result.exit_code == 0
    assert "Updating page" in overwrite_result.stdout
    check_body_and_title(page_id, body_text=new_text, title_text=page_title)
    record_pages |= get_pages_ids_from_stdout(overwrite_result.stdout)


@pytest.mark.skip
def test_render_ok():
    """Test that is supposed ot check that the page rendered confluencewiki format successfully"""
    pass


def test_skip_in_space_root(record_pages):
    """Tests that page is properly skipped if the user aborted the creation on the space root prompt"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "N\n"  # do create in root
                                        )
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert 'will skip the page' in result.stdout  # checking the prompt
    assert result.exit_code == 0
    assert confluence_instance.get_page_by_title(space=state.config.pages[0].page_space,
                                                 title=page_title) is None, "Page should not had been created"
    assert len(get_pages_ids_from_stdout(result.stdout)) == 0, "Found a page number when it should not be found"
    record_pages |= get_pages_ids_from_stdout(result.stdout)
