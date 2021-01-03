from typer.testing import CliRunner, Result
import pytest
from confluence_poster.main import app
from confluence_poster.poster_config import Config
from utils import (
    generate_run_cmd,
    run_with_config,
    mk_tmp_file,
    rewrite_page_file,
    replace_new_author,
)
from functools import partial
from itertools import product

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def _set_page_to_overwrite(config_file, page_no, tmp_path):
    return mk_tmp_file(
        config_to_clone=config_file,
        tmp_path=tmp_path,
        key_to_update=f"pages.page{page_no}.force_overwrite",
        value_to_update=True,
    )


def test_force_overwrite_one_page(tmp_path, setup_page):
    config_file, _ = setup_page(1)
    new_config = _set_page_to_overwrite(config_file, 1, tmp_path)
    new_config = replace_new_author(new_config, tmp_path)
    rewrite_page_file(Config(new_config).pages[0].page_file)

    result: Result = run_with_config(new_config)
    assert result.exit_code == 0
    assert "Updating page" in result.stdout
    assert "force overwrite" in result.stdout


@pytest.mark.parametrize(
    "overwrite_pages",
    tuple(product((True, False), repeat=2)),
    ids=lambda tup: f"User does {'not ' * (not tup[0])}overwrite first page, "
    f"does {'not ' * (not tup[1])}overwrite second",
)
def test_force_overwrite_two_pages(overwrite_pages, tmp_path, setup_page):
    """Checks for multiple pages force overwrite flag is set <=> page is updated if author is changed"""
    pages_obj = {1: {}, 2: {}}
    config_file, (
        pages_obj[1]["page_id"],
        pages_obj[1]["page_title"],
        pages_obj[2]["page_id"],
        pages_obj[2]["page_title"],
    ) = setup_page(2)
    new_config = replace_new_author(config_file, tmp_path)
    for page_no in range(2):
        if overwrite_pages[page_no]:
            new_config = _set_page_to_overwrite(
                config_file=new_config, page_no=page_no + 1, tmp_path=tmp_path
            )
        rewrite_page_file(Config(new_config).pages[page_no].page_file)

    result: Result = run_with_config(new_config)
    assert result.exit_code == 0

    for page_no in range(2):
        assert (
            f"Updating page #{pages_obj[page_no+1]['page_id']}" in result.stdout
        ) == overwrite_pages[page_no]


def test_force_flag_single_page(tmp_path, setup_page):
    """Tests that the --force flag works with force_overwrite flag - page gets updated"""
    config_file, _ = setup_page(1)
    new_config = _set_page_to_overwrite(config_file, 1, tmp_path)
    new_config = replace_new_author(new_config, tmp_path)
    rewrite_page_file(Config(new_config).pages[0].page_file)

    result: Result = run_with_config(new_config, pre_args=["--force"])
    assert result.exit_code == 0
    assert "Updating page" in result.stdout
    assert "force overwrite" not in result.stdout
