from typer.testing import CliRunner, Result
import pytest
from utils import (
    generate_run_cmd,
    run_with_config,
    create_single_page_input,
    mk_tmp_file,
)
from functools import partial
from confluence_poster.main import app


pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_warn_user_could_not_guess_file(tmp_path, make_one_page_config):
    config_file, config = make_one_page_config

    config_file = mk_tmp_file(
        tmp_path=tmp_path,
        config_to_clone=config_file,
        key_to_update="pages.page1.page_file",
        value_to_update="filename_no_extension",
    )

    result: Result = run_with_config(
        config_file=config_file,
        input=create_single_page_input,
    )
    assert "--help" in result.stdout
    assert result.exit_code == 1
