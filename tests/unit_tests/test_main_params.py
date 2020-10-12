from typer.testing import CliRunner
from confluence_poster.main import app
from confluence_poster.main import main, state
from utils import mk_tmp_file


runner = CliRunner()


def test_app_no_params_ok():
    """Tests that passing no parameters works. Should output the help section"""
    result = runner.invoke(app)
    assert result.exit_code == 0
    # Just gonna check the first line
    assert main.__doc__.split('\n')[0] in result.stdout


def test_app_nonexisting_config():
    """Tries running command with a nonexistent config file specified"""
    _ = runner.invoke(app, ['--config', 'nonexistent_file'])
    assert _.exit_code == 2


def test_different_config(tmp_path):
    """Tests that if the script reads from a specific config, not the default one"""
    new_name = "different config"
    config_file = mk_tmp_file(tmp_path, key_to_update="pages.page1.page_name", value_to_update=new_name)
    _ = runner.invoke(app, ['--config', str(config_file), 'validate'])
    assert _.exit_code == 0
    assert state.config.pages[0].page_name == new_name


def test_page_title_specified_two_pages(tmp_path):
    config_file = mk_tmp_file(tmp_path, key_to_update="pages.page2", value_to_update={"page_name": "Page2",
                                                                                      "page_file": "page2.txt"})
    _ = runner.invoke(app, ['--config', str(config_file), '--page-name', 'Default name', 'validate'])
    assert _.exit_code == 1
    assert "Page title specified as a parameter" in _.stdout


def test_no_passwords_anywhere(tmp_path):
    """Checks that if there are no passwords specified anywhere, the validation fails"""
    config_file = mk_tmp_file(tmp_path, key_to_pop="auth.password")
    _ = runner.invoke(app, ['--config', str(config_file), 'validate'])
    assert _.exit_code == 1
    assert "Password is not specified" in _.stdout


def test_password_from_cmdline():
    """Tests that password is parsed correctly from command line and is applied"""
    test_password = "cmdline_password"
    _ = runner.invoke(app, ['--password', test_password, 'validate'])
    assert _.exit_code == 0
    assert state.confluence_instance.password == test_password


def test_password_from_environment(monkeypatch):
    env_password = 'my_password_in_environment'
    monkeypatch.setenv('CONFLUENCE_PASSWORD', env_password)
    _ = runner.invoke(app, ['validate'])
    assert _.exit_code == 0
    assert state.confluence_instance.password == env_password


def test_one_page_no_title_in_config(tmp_path):
    """Checks that script runs correctly if no name is specified in config, but one is provided in cmdline"""
    page_name = "test_page"
    config_file = mk_tmp_file(tmp_path, key_to_pop="pages.page1.page_name")
    _ = runner.invoke(app, ['--page-name', page_name, '--config', str(config_file), 'validate'])
    assert state.config.pages[0].page_name == page_name


def test_debug_is_state():
    result = runner.invoke(app, ['--debug', 'validate'])
    assert result.exit_code == 0
    assert state.debug


def test_force_in_state():
    result = runner.invoke(app, ['--force', 'validate'])
    assert result.exit_code == 0
    assert state.force


def test_cloud_api(tmp_path):
    result = runner.invoke(app, ['--force', 'validate'])
    assert result.exit_code == 0
    assert state.confluence_instance.api_version == "latest"
    not_cloud_config = mk_tmp_file(tmp_path, key_to_update="auth.is_cloud", value_to_update=True)
    result = runner.invoke(app, ['--config', str(not_cloud_config), '--force', 'validate'])
    assert result.exit_code == 0
    assert state.confluence_instance.api_version == "cloud"
