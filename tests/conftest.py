import pytest
from utils import (
    join_input,
    run_with_config,
    confluence_instance,
    generate_local_config,
    fake_title_generator,
    fake_content_generator,
    get_pages_ids_from_stdout,
    generate_run_cmd,
)
from typer.testing import CliRunner
from atlassian import errors
from confluence_poster.main import app
from typing import Tuple, List


@pytest.fixture(scope="session", autouse=True)
def record_pages():
    """Cleans up created pages. The created_pages set is manipulated through inspect module when the runner command
    is executed."""
    created_pages = set()
    yield created_pages

    # Teardown
    for page_id in created_pages:
        try:
            confluence_instance.remove_page(page_id=page_id, recursive=True)
        except errors.ApiError as e:
            # Discarding 404-d pages, they were probably already removed
            if e.args[0].startswith("There is no content"):
                pass
            else:
                raise e
    # check for any py test pages?


@pytest.fixture(scope="function", autouse=False)
def setup_page(tmp_path, record_pages):
    """Pre-creates pages"""

    def _create_pages(page_count: int = 1) -> Tuple[str, List[Tuple[int, str]]]:
        page_list = []
        config_file, config = generate_local_config(tmp_path, pages=page_count)
        runner = CliRunner()
        run_cmd = generate_run_cmd(runner=runner, app=app, default_args=["post-page"])
        result = run_with_config(
            input=join_input(("Y", "N", "Y") * page_count),
            config_file=config_file,
            record_pages=record_pages,
            default_run_cmd=run_cmd,
        )
        assert result.exit_code == 0
        created_page_ids = get_pages_ids_from_stdout(result.stdout)
        for number, page in enumerate(config.pages):
            page_list += (created_page_ids[number], page.page_title)

        return config_file, page_list

    return _create_pages
