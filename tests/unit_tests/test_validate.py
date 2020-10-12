import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import mk_tmp_file
from typing import List, Union
from functools import partial
from os import environ
"""This module requires an instance of confluence running. The tests will be done against it. To skip this module
set 'VALIDATE_ONLINE' environment variable to something other than 'yes'.

If run, this test uses 'local_config.toml' file which is not provided in the repo for security reasons. 
If you do not have a Confluence instance to test, feel free to reach out to the project maintainer."""


pytestmark = pytest.mark.skipif(environ.get("VALIDATE_ONLINE", None) != "yes",
                                reason="Environment variable is not set to test against an instance of Confluence")

runner = CliRunner()
real_confluence_config = 'local_config.toml'
default_params = ['--config', real_confluence_config, 'validate', '--online']
mk_tmp_file = partial(mk_tmp_file, config_to_clone=real_confluence_config)


def run_with_config(config: str = real_confluence_config, other_args: Union[List, None] = None) -> Result:
    if other_args is None:
        other_args = []
    return runner.invoke(app, ['--config', config, 'validate', '--online'] + other_args)


def test_all_ok():
    """Validates that the validate --online does not break during execution"""
    result = run_with_config()
    assert "Validating settings" in result.stdout
    assert "Trying to get" in result.stdout
    assert "Validation successful" in result.stdout
    assert "Got space id" in result.stdout


def test_could_not_connect(tmp_path):
    """Checks that validation fails against a non-existent instance of Confluence"""
    config = mk_tmp_file(tmp_path, key_to_update="auth.confluence_url", value_to_update="http://localhost:64000")
    result = run_with_config(str(config))
    assert result.exit_code == 1
    assert "Could not connect" in result.stdout


def test_nonexistent_space(tmp_path):
    """Checks that the API returns the error about nonexistent space"""
    config = mk_tmp_file(tmp_path, key_to_update="pages.page1.page_space", value_to_update="nonexistent_space_key")
    result = run_with_config(str(config))
    assert result.exit_code == 1
    assert "API error" in result.stdout
