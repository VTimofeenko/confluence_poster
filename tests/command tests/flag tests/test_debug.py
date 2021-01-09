import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import generate_run_cmd, run_with_config
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["--debug", "validate", "--online"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_debug_flag_warns_and_prints_options(make_one_page_config):
    config_file, config = make_one_page_config
    result: Result = run_with_config(config_file=config_file)
    assert result.exit_code == 0
    assert "Set options" in result.stdout
