from typer.testing import CliRunner
import pytest
from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    run_with_config,
    generate_local_config,
    join_input,
    get_page_id_from_stdout,
    page_created,
)
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


@pytest.mark.parametrize(
    "page_count",
    list(range(1, 9)),
    ids=lambda page_count: f"Create {page_count} pages with force-create flag",
)
def test_force_create_pages(tmp_path, page_count):
    """Runs confluence_poster post-page --force-create"""
    config_file, config = generate_local_config(tmp_path, pages=page_count)

    result = run_with_config(
        config_file=config_file,
        pre_args=["--force-create"],
        input=join_input(("N", "Y") * page_count),
    )
    assert result.exit_code == 0
    assert "Should it be created?" not in result.stdout  # flag overwrites the prompt
    for page in config.pages:
        assert page_created(
            page.page_title, page.page_space
        ), "Page was supposed to be created"
