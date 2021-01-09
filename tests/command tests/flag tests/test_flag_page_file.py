from functools import partial

from bs4 import BeautifulSoup

import pytest
from typer.testing import CliRunner, Result

from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    run_with_config,
    generate_fake_page,
    create_single_page_input,
    get_page_id_from_stdout,
    get_page_body,
)

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


@pytest.mark.parametrize(
    "file_format",
    ("html", "confluencewiki", "markdown"),
    ids=lambda _format: "`confluence_poster --page-file - --force-create post-page "
    f"--create-in-space-root --file-format {_format}`",
)
def test_post_new_page_stdin(make_one_page_config, tmp_path, file_format):
    """Tests posting three sources with the effectively same text"""
    config_file, config = make_one_page_config

    content = {
        "html": """<h1>Title</h1>
<ul>
<li>one</li>
<li>two</li>
</ul>""",
        "confluencewiki": """h1. Title
* one
* two""",
        "markdown": """# Title
* one
* two""",
    }

    result: Result = run_with_config(
        config_file=config_file,
        other_args=[
            "-",
            "--force-create",
            "post-page",
            "--create-in-space-root",
            "--file-format",
            file_format,
        ],
        input=content[file_format],
    )
    assert result.exit_code == 0
    assert BeautifulSoup(
        get_page_body(get_page_id_from_stdout(result.stdout)),
        features="lxml",
    ) == BeautifulSoup(
        content["html"],
        features="lxml",
    )


@pytest.mark.parametrize(
    "text_source",
    ("-", "file"),
    ids=lambda source: f"`confluence_poster --page-file {source} convert-markdown",
)
def test_convert_markdown(make_one_page_config, tmp_path, text_source):
    config_file, config = make_one_page_config
    md_text = "# Header\nTest\n\n* One\n* Two"
    if text_source == "file":
        md_file = tmp_path / "file.md"
        md_file.write_text(md_text)
        _source = md_file
        _input = ""
    else:
        _source = "-"
        _input = md_text

    result: Result = run_with_config(
        config_file=config_file,
        other_args=[
            _source,
            "--force-create",
            "convert-markdown",
        ],
        input=_input,
    )
    assert result.exit_code == 0
    assert (
        result.stdout
        == """<h1>Header</h1>
<p>Test</p>
<ul>
<li>One</li>
<li>Two</li>
</ul>
"""
    )


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
