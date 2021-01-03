import pytest
from typer.testing import CliRunner
from utils import (
    replace_new_author,
    rewrite_page_file,
    run_with_config,
    generate_run_cmd,
    get_page_body,
    check_body_and_title,
)
from confluence_poster.main import app
from confluence_poster.poster_config import Config
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


@pytest.mark.parametrize(
    "force_flag",
    [True, False],
    ids=lambda flag: f"Runs confluence_poster {'--force '* flag} post-page",
)
def test_post_force_overwrite_other_author(force_flag, tmp_path, setup_page):
    """Checks that force flag overwrites page if the author is different"""
    config_file, (page_id, page_title) = setup_page(1)
    original_username = Config(config_file).author
    new_config = replace_new_author(config_file=config_file, tmp_path=tmp_path)
    new_text = rewrite_page_file(Config(new_config).pages[0].page_file)
    new_username = Config(new_config).author

    result = run_with_config(
        config_file=new_config,
        pre_args=["--force"] * force_flag,
    )
    assert result.exit_code == 0

    if force_flag:
        assert (
            "Updating page" in result.stdout
        ), "User should be notified an update is happening"
        assert new_text in get_page_body(page_id), "Page should had been updated"
        check_body_and_title(page_id, body_text=new_text, title_text=page_title)
    else:
        assert "Flag 'force' is not set and last author" in result.stdout, (
            "User should be notified why the script " "is not updating anything"
        )
        assert (
            original_username in result.stdout
        ), "The original username should be mentioned in the script output"
        assert (
            new_username in result.stdout
        ), "The author_to_check username should be mentioned in the script output"
        assert new_text not in get_page_body(
            page_id
        ), "Page should not had been updated"


@pytest.mark.parametrize(
    "force_flag",
    [False, True],
    ids=lambda flag: f"Updates page as the same user with{'out' * flag} --force flag",
)
def test_create_and_overwrite_page(force_flag, setup_page):
    """Creates a page and tries to overwrite it as the same user. Checks that the force_flag does not matter"""
    config_file, (page_id, page_title) = setup_page(1)
    new_text = rewrite_page_file(Config(config_file).pages[0].page_file)

    overwrite_result = run_with_config(
        config_file=config_file,
        pre_args=["--force"] * force_flag,
    )
    assert overwrite_result.exit_code == 0
    assert "Updating page" in overwrite_result.stdout
    check_body_and_title(page_id, body_text=new_text, title_text=page_title)
