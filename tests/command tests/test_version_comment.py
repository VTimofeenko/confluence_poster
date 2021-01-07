import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    run_with_config,
    generate_local_config,
    mk_fake_file,
    confluence_instance,
)
from atlassian.confluence import Confluence
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["post-page", "--version-comment"]
)
run_with_config = partial(run_with_config, default_run_cmd=default_run_cmd)


def _get_version_comment(page_title: str, space: str, confluence: Confluence) -> str:
    page_id = confluence.get_page_id(space=space, title=page_title)
    history = confluence.history(page_id)
    return history["lastUpdated"]["message"]


@pytest.mark.parametrize(
    "mode", ("create", "update"), ids=lambda mode: f"User {mode}s page with comment"
)
def test_single_page_with_comment(mode, tmp_path):
    config_file, config = generate_local_config(tmp_path=tmp_path, pages=1)

    def run_with_comment(comment: str):
        _result: Result = run_with_config(
            config_file=config_file, input="Y\n" "N\n" "Y\n", other_args=[comment]
        )
        assert _result.exit_code == 0
        return _result

    # Confluence does not support creating page and specifying version comment
    result = run_with_comment(comment="Test create comment")
    assert "Confluence API does not support" in result.stdout
    if mode == "update":
        version_comment = "Test update comment"
        # update the text of the page
        mk_fake_file(
            tmp_path, filename=config.pages[0].page_title.lower().replace(" ", "_")
        )
        run_with_comment(comment=version_comment)
        assert (
            _get_version_comment(
                page_title=config.pages[0].page_title,
                space="LOC",
                confluence=confluence_instance,
            )
            == version_comment
        )


@pytest.mark.parametrize(
    "apply_config_answer",
    ["A", "F", "N", ""],
    ids=[
        "User applies comment to all pages",
        "User applies comment to the first page",
        "User does not apply config",
        "User accepts default choice",
    ],
)
def test_multiple_pages_with_comment(apply_config_answer, tmp_path):
    config_file, config = generate_local_config(tmp_path=tmp_path, pages=2)
    # create the pages
    result = run_with_config(
        config_file=config_file,
        input=f"{apply_config_answer}\n"
        "Y\n"  # create first page
        "N\n"  # do not look for parent
        "Y\n"  # create in root
        "Y\n"  # create second page
        "N\n"
        "Y\n",
        other_args=["create_comment"],
    )
    assert result.exit_code == 0

    for page in config.pages:
        # Regenerate content of page
        mk_fake_file(tmp_path, filename=page.page_title.lower().replace(" ", "_"))

    result = run_with_config(
        config_file=config_file,
        input=f"{apply_config_answer}\n"
        "Y\n"  # create first page
        "N\n"  # do not look for parent
        "Y\n"  # create in root
        "Y\n"  # create second page
        "N\n"
        "Y\n",
        other_args=["update_comment"],
    )
    assert result.exit_code == 0
    if apply_config_answer in {"A", ""}:
        for page in config.pages:
            assert (
                _get_version_comment(
                    page_title=page.page_title,
                    space=page.page_space,
                    confluence=confluence_instance,
                )
                == "update_comment"
            )
    elif apply_config_answer == "F":
        for page in config.pages:
            if page == config.pages[0]:
                _checked_comment = "update_comment"
            else:
                _checked_comment = ""
            assert (
                _get_version_comment(
                    page_title=page.page_title,
                    space=page.page_space,
                    confluence=confluence_instance,
                )
                == _checked_comment
            )
    elif apply_config_answer == "N":
        for page in config.pages:
            assert (
                _get_version_comment(
                    page_title=page.page_title,
                    space=page.page_space,
                    confluence=confluence_instance,
                )
                == ""
            )
