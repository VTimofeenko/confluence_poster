from typer.testing import CliRunner

# noinspection PyUnresolvedReferences
from confluence_poster.main import app, main, state
from confluence_poster.main_helpers import StateConfig
from utils import mk_tmp_file, generate_fake_page
import pytest


runner = CliRunner()
pytestmark = pytest.mark.offline


@pytest.fixture(scope="module")
def teardown_state():
    """Fixture to clear the state after this module is done. Necessary to prevent state being polluted by pytest."""
    yield
    # noinspection PyGlobalUndefined
    global state
    state = StateConfig()


@pytest.mark.parametrize("config_file", [None, "other"])
def test_different_config(tmp_path, config_file):
    """Tests that if the script reads from a specific config, not the default one

    If the config is None - nonexistent file is provided"""
    new_page_name = "different config"
    if config_file is not None:
        _config_file = mk_tmp_file(
            tmp_path,
            key_to_update="pages.page1.page_title",
            value_to_update=new_page_name,
        )
    else:
        _config_file = "nonexistent_config"

    result = runner.invoke(app, ["--config", str(_config_file), "validate"])
    if config_file is not None:
        assert result.exit_code == 0
    else:
        assert result.exit_code == 1
        assert (
            "create-config" in result.stdout
        ), "User should be prompted to create config through wizard"
        assert type(result.exception) is FileNotFoundError


@pytest.mark.parametrize("param", ["page_title", "parent_page_title"])
def test_page_title_specified_two_pages(tmp_path, param):
    """For parameters that require that only one page is in config - make sure exception is raised if there are
    more pages in the config"""
    config_file = mk_tmp_file(
        tmp_path,
        key_to_update="pages.page2",
        value_to_update={"page_title": "Page2", "page_file": "page2.txt"},
    )
    _ = runner.invoke(
        app,
        [
            "--config",
            str(config_file),
            f"--{param.replace('_', '-')}",
            "Default name",
            "validate",
        ],
    )
    assert _.exit_code == 1
    assert "Please specify them in the config." in _.stdout


@pytest.mark.parametrize("password_source", [None, "cmdline", "environment", "config"])
def test_no_passwords_anywhere(tmp_path, password_source, monkeypatch):
    """Checks that the password is applied, depending on the source.
    If source is 'None' - no password is supplied anywhere and validation fails."""
    config_file = mk_tmp_file(tmp_path, key_to_pop="auth.password")
    if password_source is None:
        result = runner.invoke(app, ["--config", str(config_file), "validate"])
    else:
        if password_source == "cmdline":
            result = runner.invoke(
                app,
                [
                    "--config",
                    str(config_file),
                    "--password",
                    password_source,
                    "validate",
                ],
            )
        elif password_source == "environment":
            monkeypatch.setenv("CONFLUENCE_PASSWORD", password_source)
            result = runner.invoke(app, ["--config", str(config_file), "validate"])
        else:
            config_file = mk_tmp_file(
                tmp_path, key_to_update="auth.password", value_to_update=password_source
            )
            result = runner.invoke(app, ["--config", str(config_file), "validate"])

    if password_source is None:
        assert result.exit_code == 1
        assert "Password is not specified" in result.stdout
    else:
        assert result.exit_code == 0
        assert state.confluence_instance.password == password_source


def test_one_page_no_title_in_config(tmp_path):
    """Checks that script runs correctly if no name is specified in config, but one is provided in cmdline"""
    page_title = "test_page"
    config_file = mk_tmp_file(tmp_path, key_to_pop="pages.page1.page_title")
    config_file = mk_tmp_file(
        tmp_path, config_to_clone=config_file, key_to_pop="pages.page2"
    )
    _ = runner.invoke(
        app, ["--page-title", page_title, "--config", str(config_file), "validate"]
    )
    assert state.config.pages[0].page_title == page_title


@pytest.mark.parametrize(
    "is_cloud",
    (True, False),
    ids=lambda is_cloud: f"Create config with is_cloud set to {is_cloud}, runs `confluence_poster validate`",
)
def test_cloud_api(tmp_path, is_cloud):
    """Checks that the logic to handle what version of Atlassian API is to be used works well"""
    config = mk_tmp_file(
        tmp_path, key_to_update="auth.is_cloud", value_to_update=is_cloud
    )
    result = runner.invoke(app, ["--config", str(config), "validate"])
    assert result.exit_code == 0
    if is_cloud:
        assert state.confluence_instance.api_version == "cloud"
    else:
        assert state.confluence_instance.api_version == "latest"


def test_page_file_not_specified_filter_mode(tmp_path, make_one_page_config):
    """Runs the command with page_file set to a real file. Checks that filter_mode is off."""
    config_file, config = make_one_page_config
    _, content, page_file = generate_fake_page(tmp_path)
    result = runner.invoke(
        app, ["--page-file", page_file, "--config", config_file, "validate"]
    )
    assert result.exit_code == 0
    assert state.filter_mode is False


def test_show_version():
    """Checks that --version flag works"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Confluence poster version" in result.stdout
