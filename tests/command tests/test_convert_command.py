import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import generate_run_cmd, run_with_config
from atlassian.confluence import Confluence
from functools import partial
from pathlib import Path

pytestmark = pytest.mark.online

runner = CliRunner(mix_stderr=False)
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["convert-markdown"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_no_extra_output_online(make_one_page_config):
    """Makes sure that there is no extra output in stdout when running the tool"""
    config_file, config = make_one_page_config
    Path(config.pages[0].page_file).write_text("# Title\n* one\n* two")

    result = run_with_config(
        config_file=config_file, other_args=["--use-confluence-converter"]
    )

    assert result.exit_code == 0
    assert result.stdout == """<h1>Title</h1> <ul> <li>one <li>two </ul>"""
    assert (
        "Consider using external tool" in result.stderr
    ), "This command uses Confluence private API, user should be warned"


def test_convert_multiple_pages():
    pass
