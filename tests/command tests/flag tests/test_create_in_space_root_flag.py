import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    run_with_config,
    join_input,
    generate_local_config,
    get_pages_ids_from_stdout,
    confluence_instance,
)
from atlassian.confluence import Confluence
from functools import partial


"""Tests the --create-in-space-root flag of post-page"""
pytestmark = pytest.mark.online

runner = CliRunner(mix_stderr=False)
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["post-page", "--create-in-space-root"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


@pytest.mark.parametrize(
    "page_count",
    list(range(1, 3)),
    ids=lambda c: f"Create {c} pages in the root with the --create-in-space-root flag",
)
def test_create_one_page_in_space_root(tmp_path, page_count):
    config_file, config = generate_local_config(tmp_path, pages=page_count)
    result: Result = run_with_config(
        config_file=config_file, input=join_input(user_input=("Y",) * page_count)
    )
    created_pages = get_pages_ids_from_stdout(result.stdout)
    assert result.exit_code == 0
    assert (
        result.stderr is ""
    )  # if parent is not found - get_parent_content_id logs to stderr
    assert len(created_pages) == page_count
    for page_id in created_pages:
        parent = confluence_instance.get_parent_content_id(page_id)
        assert parent is None, "Page should had been created in space root"
