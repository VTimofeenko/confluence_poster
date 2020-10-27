from typer.testing import CliRunner
import pytest
from confluence_poster.main import app, get_page_url
from utils import clone_local_config, \
    generate_run_cmd,\
    real_confluence_config,\
    real_config, \
    confluence_instance, \
    mk_fake_file,\
    page_created, fake_title_generator, check_body_and_title, get_page_body, get_page_title, \
    get_pages_ids_from_stdout, \
    get_page_id_from_stdout, run_with_config, \
    generate_local_config
from functools import partial
from faker import Faker


f"""This module requires an instance of confluence running. 
The tests will be done against it using a {real_confluence_config} 

This is a collection of tests on a single page"""

pytestmark = pytest.mark.online

runner = CliRunner()
mk_tmp_file = clone_local_config()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=['post-page'])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def run_with_title(page_title: str = None, fake_title=True, *args, **kwargs,):
    """Helper function to create pages with specific title. Generates fake title by default"""
    if page_title is None and fake_title:
        page_title = next(fake_title_generator)
    elif fake_title is False and page_title is None:
        raise ValueError("Fake title is False and no real title was provided")

    return run_with_config(pre_args=['--page-title', page_title], *args, **kwargs), page_title


@pytest.fixture(scope='function')
def make_one_page_config(tmp_path):
    return generate_local_config(tmp_path, pages=1)


def test_page_overridden_title(make_one_page_config):
    """Tests that the title supplied through command line is applied"""
    config_file, config = make_one_page_config
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "Y\n",  # do create in root
                                        config_file=config_file)
    assert result.exit_code == 0
    created_page_title = get_page_title(get_page_id_from_stdout(result.stdout))
    assert created_page_title == page_title, "Page title was not applied from command line"
    assert created_page_title != config.pages[0].page_title, "Page title is the same as in config," \
                                                             " should have been overwritten"


def test_post_single_page_no_parent(make_one_page_config):
    """Test with good default config, to check that everything is OK. Creates a sample page in the root of the space

    Author's note: mirrors setup_page fixture, but kept separately to make failures clearer"""
    config_file, config = make_one_page_config
    result = run_with_config(config_file=config_file,
                             input="Y\n"  # do create page
                                   "N\n"  # do not look for parent
                                   "Y\n")  # do create in root
    assert result.exit_code == 0
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert f"Page '{config.pages[0].page_title}' not found" in result.stdout
    assert "Creating page" in result.stdout
    assert "Finished processing pages" in result.stdout


@pytest.mark.parametrize("with_report", [False, True])
def test_not_create_if_refused(make_one_page_config, with_report):
    config_file, config = make_one_page_config
    result = run_with_config(input="N\n",  # it should not be created
                             pre_args=['--report'] * with_report,
                             config_file=config_file)
    assert result.exit_code == 0
    assert 'Not creating page' in result.stdout, "Script did not report that page is not created"
    assert not page_created(page_title=config.pages[0].page_title), "Page was not supposed to be created"
    assert len(get_pages_ids_from_stdout(result.stdout)) == 0, "Detected a page that was created!"

    if with_report:
        page = config.pages[0]
        assert get_page_url(page.page_title, page.page_space, confluence_instance) is None
        assert "Created pages:\nNone\nUpdated pages:\nNone\nUnprocessed pages:" in result.stdout
        assert f"{page.page_space}::{page.page_title} Reason: User cancelled creation when prompted"


@pytest.fixture(scope='function')
def setup_page(tmp_path, record_pages):
    """Pre-creates a page"""
    config_file, config = generate_local_config(tmp_path,
                                                pages=1,
                                                filename="setup_page_config.toml")
    result = run_with_config(input="Y\n"  # create page
                                   "N\n"  # do not look for parent
                                   "Y\n",  # do create in root of the space
                             config_file=config_file,
                             record_pages=record_pages)
    assert result.exit_code == 0
    return get_page_id_from_stdout(result.stdout), config.pages[0].page_title


@pytest.mark.parametrize("parent_page_title_source", ['dialog', 'cmdline', 'config'])
def test_post_single_page_with_parent(setup_page, parent_page_title_source, tmp_path):
    """Tests that the parent_page_title is applied to create the page in the proper place.
    Tests scenarios of providing the parent title in dialog (through user input), as --parent-page-title argument,
    or in config"""

    # Create the first page, it will be the parent
    parent_id, parent_page_title = setup_page
    page_title = next(fake_title_generator)

    if parent_page_title_source == 'dialog':
        result, _ = run_with_title(input=f"Y\n"  # create page
                                         f"Y\n"  # look for parent
                                         f"{parent_page_title}\n"  # title of the parent
                                         f"Y\n",  # yes, proceed to create
                                   config_file=real_confluence_config)
        assert "Which page should the script look for?" in result.stdout
        assert "URL is:" in result.stdout
        assert "Proceed to create?" in result.stdout
    else:

        if parent_page_title_source == 'cmdline':
            result = run_with_config(input=f"Y\n",  # create page
                                     pre_args=['--parent-page-title', parent_page_title, '--page-title', page_title],
                                     config_file=real_confluence_config)
        else:
            config_file = mk_tmp_file(tmp_path=tmp_path,
                                      key_to_update="pages.page1.page_parent_title",
                                      value_to_update=parent_page_title)
            result, _ = run_with_title(input=f"Y\n",  # create page
                                       config_file=config_file)
        assert "Which page should the script look for?" not in result.stdout, \
            "If the parent page title is explicitly supplied, script should not look for parent"

    assert "Found page #" in result.stdout
    assert result.exit_code == 0
    assert get_page_id_from_stdout(result.stdout) in confluence_instance.get_child_id_list(parent_id)


@pytest.mark.parametrize('force_flag', [True, False])
def test_post_force_overwrite_other_author(force_flag, tmp_path, setup_page):
    """Checks that force flag overwrites page if the author is different"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page
    original_username = real_config.author
    fake_username = Faker().user_name()

    overwrite_config = mk_tmp_file(tmp_path,
                                   config_to_clone=str(overwrite_config),
                                   key_to_update="author", value_to_update=f"Fake: {fake_username}")
    result = run_with_config(config_file=overwrite_config, pre_args=['--force'] * force_flag +
                                                                    ['--page-title', page_title])
    assert result.exit_code == 0

    if force_flag:
        assert "Updating page" in result.stdout, "User should be notified an update is happening"
        assert new_text in get_page_body(page_id), "Page should had been updated"
        check_body_and_title(page_id, body_text=new_text, title_text=page_title)
    else:
        assert "Flag 'force' is not set and last author" in result.stdout, "User should be notified why the script " \
                                                                           "is not updating anything"
        assert original_username in result.stdout, "The original username should be mentioned in the script output"
        assert fake_username in result.stdout, "The author_to_check username should be mentioned in the script " \
                                               "output"
        assert new_text not in get_page_body(page_id), "Page should not had been updated"


@pytest.mark.parametrize('force_flag', [False, True])
def test_create_and_overwrite_page(force_flag, tmp_path, setup_page):
    """Creates a page and overwrites it. Checks that the force_flag does not matter"""
    overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
    page_id, page_title = setup_page

    overwrite_result = run_with_config(config_file=overwrite_config,
                                       pre_args=['--force'] * force_flag +
                                                ['--page-title', page_title])
    assert overwrite_result.exit_code == 0
    assert "Updating page" in overwrite_result.stdout
    check_body_and_title(page_id, body_text=new_text, title_text=page_title)


def test_render_ok(tmp_path, setup_page):
    """Test that is supposed ot check that the page rendered confluencewiki format successfully"""
    page_id, page_title = setup_page

    config = mk_tmp_file(tmp_path,
                         config_to_clone=real_confluence_config,
                         key_to_update="pages.page1.page_file", value_to_update="page2.confluencewiki")
    run_with_title(page_title, config_file=config)
    assert get_page_body(page_id) == "<h1>Header</h1>\n\n<p>Some text</p>"


def test_skip_in_space_root():
    """Tests that page is properly skipped if the user aborted the creation on the space root prompt"""
    result, page_title = run_with_title(input="Y\n"  # do create page
                                              "N\n"  # do not look for parent
                                              "N\n",  # do not create in root
                                        config_file=real_confluence_config
                                        )
    assert 'Looking for page' in result.stdout
    assert 'Should it be created?' in result.stdout  # checking the prompt
    assert 'Should the script look for a parent in space' in result.stdout  # checking the prompt
    assert 'Create the page in the root' in result.stdout  # checking the prompt
    assert 'will skip the page' in result.stdout  # checking the prompt
    assert result.exit_code == 0
    assert confluence_instance.get_page_by_title(space=real_config.pages[0].page_space,
                                                 title=page_title) is None, "Page should not had been created"
    assert len(get_pages_ids_from_stdout(result.stdout)) == 0, "Found a page number when it should not be found"


@pytest.mark.parametrize("action", ["create", "update"])
def test_minor_edit(action, make_one_page_config, tmp_path, setup_page):
    """Tests that minor edit action is recorded on the page. API does not allow creation of the
     page to be a minor edit, only an update"""
    if action == "create":
        config_file, config = make_one_page_config
        result = run_with_config(config_file=config_file, pre_args=['--minor-edit'],
                                 input="Y\nN\nY\n")
        page_id = get_page_id_from_stdout(result.stdout)
    else:
        overwrite_file, new_text, overwrite_config = mk_fake_file(tmp_path, filename='overwrite')
        page_id, page_title = setup_page

        result = run_with_config(config_file=overwrite_config, pre_args=['--page-title', page_title, '--minor-edit'])

    assert result.exit_code == 0
    last_update = confluence_instance.get_content_history(page_id).get('lastUpdated')

    if action == "create":
        assert not last_update.get("minorEdit"), "Creation was marked as minor edit"
    else:
        # Looks like Atlassian stopped exposing this in the API :( no notifications are sent out though
        with pytest.raises(AssertionError):
            assert last_update.get("minorEdit"), "Page update was not marked as minor edit"


def test_create_page_under_nonexistent_parent(tmp_path, make_one_page_config):
    """Tries to create a page under a non-existent parent, ensures that it fails and reports"""
    config_file, config = make_one_page_config
    parent_page_title = next(fake_title_generator)
    config_file = mk_tmp_file(tmp_path=tmp_path,
                              config_to_clone=config_file,
                              key_to_update="pages.page1.page_parent_title",
                              value_to_update=parent_page_title)
    result = run_with_config(input=f"Y\n",  # create page
                             config_file=config_file)
    assert result.exit_code == 0
    assert f"page '{parent_page_title}' not found" in result.stdout
    assert "Skipping page" in result.stdout


def test_search_for_parent_multiple_times(make_one_page_config):
    """Checks that the user can retry searching for a parent if it is not found"""
    config_file, config = make_one_page_config
    attempts = 3  # how many times to try to look for parent
    nl = '\n'  # to work around f-string '\' limitation
    result = run_with_config(input="Y\n"  # create page
                                   f"{attempts * ('Y' + nl + next(fake_title_generator) + nl)}"  # try to look 
                                   "N\n"  # finally, refuse to look for parent
                                   "Y\n",  # create in root
                             config_file=config_file)
    assert result.exit_code == 0
    assert result.stdout.count("Should the script look for a parent in space") == attempts + 1  # +1 because refusal


def test_force_create_page(make_one_page_config):
    """Tests the force_create flag."""
    config_file, config = make_one_page_config
    result = run_with_config(input="N\nY\n",  # do not look for parent, create in root
                             other_args=['--force-create'],
                             config_file=config_file)
    assert result.exit_code == 0
    assert 'Should it be created?' not in result.stdout  # flag overwrites the prompt
    assert page_created(page_title=config.pages[0].page_title), "Page was supposed to be created"
