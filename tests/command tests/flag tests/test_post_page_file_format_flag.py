from typer.testing import CliRunner, Result
import pytest
from utils import (
    generate_run_cmd,
    run_with_config,
    generate_local_config,
    create_single_page_input,
    mk_tmp_file,
)
from functools import partial
from confluence_poster.main import app


pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


@pytest.mark.parametrize(
    "file_format",
    ["confluencewiki", "markdown", "html", "None"],
    ids=lambda f: f"Run `confluence_poster post-page --file-format {f}`",
)
def test_all_file_formats(make_one_page_config, file_format):
    config_file, config = make_one_page_config

    result: Result = run_with_config(
        config_file=config_file,
        input=create_single_page_input,
        other_args=["--file-format", file_format],
    )
    assert result.exit_code == 0


def test_could_not_guess_file_format(make_one_page_config, tmp_path):
    config_file, config = make_one_page_config
    config_file = mk_tmp_file(
        tmp_path=tmp_path,
        config_to_clone=config_file,
        key_to_update="pages.page1.page_file",
        value_to_update="some_file_no_ext",
    )
    result: Result = run_with_config(
        config_file=config_file, input=create_single_page_input
    )
    assert result.exit_code == 1
    assert "Consider specifying it manually" in result.stdout


def test_error_if_multiple_pages(tmp_path):
    config_file, config = generate_local_config(tmp_path, pages=2)
    result: Result = run_with_config(
        config_file=config_file,
        input=create_single_page_input,
        other_args=["--file-format", "html"],
    )
    assert "Consider adding it to the config file." in result.stdout
    assert result.exit_code == 1
