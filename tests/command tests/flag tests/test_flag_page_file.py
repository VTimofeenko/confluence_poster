import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    run_with_config,
    generate_fake_page,
    join_input,
    create_single_page_input,
    get_page_id_from_stdout,
    get_page_body,
)
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner(mix_stderr=False)
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["--page-file"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_post_page_with_real_file(make_one_page_config, tmp_path):
    config_file, config = make_one_page_config
    _, content, page_file = generate_fake_page(tmp_path)

    result: Result = run_with_config(
        config_file=config_file,
        other_args=[page_file, "post-page"],
        input=create_single_page_input,
    )
    assert result.exit_code == 0
    assert get_page_body(get_page_id_from_stdout(result.stdout)) == f"<p>{content}</p>"


# test with format and without
def test_post_new_page_stdin(make_one_page_config, tmp_path):
    config_file, config = make_one_page_config
    _, content, page_file = generate_fake_page(tmp_path)
    result: Result = run_with_config(
        config_file=config_file,
        other_args=[
            "-",
            "--force-create",
            "post-page",
            "--create-in-space-root",
            "--file-format",
            "confluencewiki",
        ],
        input=content,
    )
    assert result.exit_code == 0
    assert get_page_body(get_page_id_from_stdout(result.stdout)) == f"<p>{content}</p>"


def test_convert_markdown():
    pass


@pytest.mark.parametrize(
    "command",
    ("validate", "create-config"),
    ids=lambda cmd: f"`confluence_poster --page-file - ${cmd}`, callback should exit with code 3",
)
def test_other_commands(make_one_page_config, tmp_path, command):
    config_file, config = make_one_page_config
    _, content, page_file = generate_fake_page(tmp_path)
    result: Result = run_with_config(
        config_file=config_file,
        other_args=["-", "--force-create", f"{command}"],
        input=content,
    )
    assert result.exit_code == 3
    assert "not compatible" in result.stderr
