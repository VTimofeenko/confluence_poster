from typer.testing import CliRunner
from confluence_poster.main import app
from confluence_poster.main import main, state
from utils import mk_tmp_file
import pytest
from dataclasses import asdict


runner = CliRunner()
pytestmark = pytest.mark.offline


def test_app_no_params_ok():
    """Tests that passing no parameters works. Should output the help section"""
    result = runner.invoke(app)
    assert result.exit_code == 0
    # Just gonna check the first line
    assert main.__doc__.split("\n")[0] in result.stdout


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
        assert state.config.pages[0].page_title == new_page_name
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
    assert "Page title specified as a parameter" in _.stdout


@pytest.mark.parametrize("password_source", [None, "cmdline", "environment", "config"])
def test_no_passwords_anywhere(tmp_path, password_source, monkeypatch):
    """Checks that the password is applied, depending on the source.
    If source is 'None' - no password is supplied anywhere and validation fails."""
    if password_source is None:
        config_file = mk_tmp_file(tmp_path, key_to_pop="auth.password")
        result = runner.invoke(app, ["--config", str(config_file), "validate"])
    else:
        if password_source == "cmdline":
            result = runner.invoke(app, ["--password", password_source, "validate"])
        elif password_source == "environment":
            monkeypatch.setenv("CONFLUENCE_PASSWORD", password_source)
            result = runner.invoke(app, ["validate"])
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


@pytest.mark.parametrize("param", ["debug", "force", "minor_edit", "force_create"])
def test_binary_parameter_in_state(param):
    """Checks that the binary parameters are reflected in state."""
    result = runner.invoke(app, [f'--{param.replace("_", "-")}', "validate"])
    assert result.exit_code == 0
    assert asdict(state).get(param)


def test_cloud_api(tmp_path):
    """Checks that the logic to handle what version of Atlassian API is to be used works well"""
    result = runner.invoke(app, ["--force", "validate"])
    assert result.exit_code == 0
    assert state.confluence_instance.api_version == "latest"
    not_cloud_config = mk_tmp_file(
        tmp_path, key_to_update="auth.is_cloud", value_to_update=True
    )
    result = runner.invoke(
        app, ["--config", str(not_cloud_config), "--force", "validate"]
    )
    assert result.exit_code == 0
    assert state.confluence_instance.api_version == "cloud"


def test_show_version():
    """Checks that --version flag works"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Confluence poster version" in result.stdout
