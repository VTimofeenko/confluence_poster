import pytest
from typer.testing import CliRunner
from confluence_poster.main import app
from confluence_poster.main import get_page_url
from utils import (
    generate_run_cmd,
    run_with_config,
    join_input,
    page_created,
    get_pages_ids_from_stdout,
    confluence_instance,
)
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["--report", "post-page"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)

# TODO: more tests
# TODO: test --quiet interaction


def test_post_page_report(make_one_page_config):
    config_file, config = make_one_page_config
    result = run_with_config(input=join_input("N"), config_file=config_file)

    assert result.exit_code == 0
    assert (
        "Not creating page" in result.stdout
    ), "Script did not report that page is not created"
    assert not page_created(
        page_title=config.pages[0].page_title
    ), "Page was not supposed to be created"
    assert (
        len(get_pages_ids_from_stdout(result.stdout)) == 0
    ), "Detected a page that was created!"
    page = config.pages[0]
    assert get_page_url(page.page_title, page.page_space, confluence_instance) is None
    assert (
        "Created pages:\nNone\nUpdated pages:\nNone\nUnprocessed pages:"
        in result.stdout
    )
    assert (
        f"{page.page_space}::{page.page_title} Reason: User cancelled creation when prompted"
        in result.stdout
    )
