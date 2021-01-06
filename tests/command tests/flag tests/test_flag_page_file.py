import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import generate_run_cmd, run_with_config, generate_fake_page
from functools import partial

pytestmark = pytest.mark.skip

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["--page-file"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_post_page_with_file(make_one_page_config, tmp_path):
    config_file, config = make_one_page_config
    _, content, page_file = generate_fake_page(tmp_path)

    result: Result = run_with_config(
        config_file=config_file, other_args=[page_file, "post-page"]
    )
    assert result.exit_code == 0


# test with format and without
def test_post_page_stdin():
    pass


def test_convert_markdown():
    pass


def test_other_commands():
    pass
