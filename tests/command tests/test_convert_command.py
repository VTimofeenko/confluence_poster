import pytest
from typer.testing import CliRunner
from confluence_poster.main import app
from utils import generate_run_cmd, run_with_config
from functools import partial
from pathlib import Path

pytestmark = pytest.mark.online

runner = CliRunner(mix_stderr=False)
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["convert-markdown"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def test_convert_command_default_behavior(make_one_page_config):
    """Makes sure that there is no extra output in stdout when running the tool"""
    config_file, config = make_one_page_config
    Path(config.pages[0].page_file).write_text("# Title\n* one\n* two")

    result = run_with_config(config_file=config_file, other_args=[])

    assert result.exit_code == 0
    assert (
        result.stdout
        == """<h1>Title</h1>
<ul>
<li>one</li>
<li>two</li>
</ul>
"""
    )


def test_convert_online(make_one_page_config):
    config_file, config = make_one_page_config
    Path(config.pages[0].page_file).write_text("# Title\n* one\n* two")

    result = run_with_config(
        config_file=config_file, other_args=["--use-confluence-converter"]
    )
    assert result.stdout == """<h1>Title</h1> <ul> <li>one <li>two </ul> \n"""
    assert (
        "Using the converter built into Confluence which is labeled as private API."
        in result.stderr
    ), "This command uses Confluence private API, user should be warned"
    assert (
        "file-format html" in result.stderr
    ), "Recommendation about file format should be given"


def test_convert_multiple_pages(make_two_page_config):
    config_file, config = make_two_page_config
    result = run_with_config(config_file=config_file)

    assert result.exit_code == 1
