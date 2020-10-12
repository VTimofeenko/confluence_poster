from typer.testing import CliRunner
from confluence_poster.main import app
from confluence_poster.main import main
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


def test_page_title_specified_two_pages(tmp_path):
    config_file = mk_tmp_file(tmp_path, key_to_update="pages.page2", value_to_update={"page_title": "Page2",
                                                                                      "page_path": "page2.txt"})
    _ = runner.invoke(app, ['--config', str(config_file), '--page-title', 'Default name', 'validate'])
    assert _.exit_code == 1
