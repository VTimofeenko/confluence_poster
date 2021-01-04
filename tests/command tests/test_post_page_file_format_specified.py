from typer.testing import CliRunner, Result
import pytest
from utils import (
    clone_local_config,
    generate_run_cmd,
    real_confluence_config,
    real_config,
    confluence_instance,
    mk_fake_file,
    page_created,
    fake_title_generator,
    get_page_body,
    get_page_title,
    get_pages_ids_from_stdout,
    get_page_id_from_stdout,
    run_with_config,
    generate_local_config,
    join_input,
    create_single_page_input,
    mk_tmp_file,
)
from functools import partial
from confluence_poster.main import app


pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["post-page", "--file-format"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


@pytest.mark.parametrize(
    "file_format",
    ["confluencewiki", "markdown", "html", "None"],
    ids=lambda f: f"Run confluence_poster post-page --file-format {f}",
)
def test_warn_user_could_not_guess_file(make_one_page_config, file_format):
    config_file, config = make_one_page_config

    result: Result = run_with_config(
        config_file=config_file,
        input=create_single_page_input,
        other_args=[file_format],
    )
    if file_format != "markdown":
        assert result.exit_code == 0
    else:
        assert result.exit_code == 1


def test_error_if_multiple_pages(tmp_path):
    config_file, config = generate_local_config(tmp_path, pages=2)
    result: Result = run_with_config(
        config_file=config_file,
        input=create_single_page_input,
        other_args=["html"],
    )
    assert "Consider adding it to the config file." in result.stdout
    assert result.exit_code == 1
