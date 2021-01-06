from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import clone_local_config, generate_run_cmd, run_with_config
import pytest
from functools import partial

"""This module requires an instance of confluence running. 

If run, this test uses 'local_config.toml' file which is not provided in the repo for security reasons. 
If you do not have a Confluence instance to test, feel free to reach out to the project maintainer."""


pytestmark = pytest.mark.online

runner = CliRunner(mix_stderr=False)
mk_local_config = clone_local_config()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["validate"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_all_ok(make_one_page_config):
    """Validates that the validate --online does not break during execution"""
    config_file, config = make_one_page_config
    result: Result = run_with_config(config_file=config_file, other_args=["--online"])
    assert "Validating settings" in result.stdout
    assert "Trying to get" in result.stdout
    assert "Validation successful" in result.stdout
    assert "Got space id" in result.stdout


def test_could_not_connect(tmp_path):
    """Checks that validation fails against a non-existent instance of Confluence"""
    config = mk_local_config(
        tmp_path,
        key_to_update="auth.confluence_url",
        value_to_update="http://localhost:64000",
    )
    result: Result = run_with_config(config_file=config, other_args=["--online"])
    assert result.exit_code == 1
    assert "Could not connect" in result.stderr


def test_nonexistent_space(tmp_path):
    """Checks that the API returns the error about nonexistent space"""
    config = mk_local_config(
        tmp_path,
        key_to_update="pages.page1.page_space",
        value_to_update="nonexistent_space_key",
    )
    result: Result = run_with_config(config_file=config, other_args=["--online"])
    assert result.exit_code == 1
    assert "API error" in result.stderr


@pytest.mark.parametrize(
    "online",
    (True, False),
    ids=lambda online: f"`confluence_poster --quiet validate{' --online' * online}` produces no output",
)
def test_validate_with_quiet(online, make_one_page_config):
    config_file, config = make_one_page_config
    result: Result = run_with_config(
        config_file=config_file, pre_args=["--quiet"], other_args=["--online"] * online
    )
    assert result.exit_code == 0
    assert result.stdout == ""
