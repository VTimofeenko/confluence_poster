import pytest
from typer.testing import CliRunner, Result
from confluence_poster.main import app
from utils import (
    generate_run_cmd,
    confluence_instance,
    run_with_config,
    generate_local_config,
    get_page_id_from_stdout,
    fake_content_generator,
    page_created,
    fake_title_generator,
    get_pages_ids_from_stdout,
)
from functools import partial

pytestmark = pytest.mark.online

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["post-page", "--upload-files"]
)
upload_files = partial(run_with_config, default_run_cmd=partial(default_run_cmd))


@pytest.fixture(scope="function")
def setup_page(tmp_path, record_pages):
    """Prepares a page to upload files to"""
    config_path, config = generate_local_config(tmp_path, pages=1)
    post_page_run_cmd = generate_run_cmd(
        runner=runner, app=app, default_args=["post-page"]
    )
    create_page = partial(run_with_config, default_run_cmd=post_page_run_cmd)
    result = create_page(
        config_file=config_path, record_pages=record_pages, input="Y\nN\nY\n"
    )
    assert result.exit_code == 0
    return get_page_id_from_stdout(result.stdout), config_path


@pytest.fixture(scope="function")
def gen_attachments(tmp_path):
    result = []
    d = tmp_path / "attachments"
    d.mkdir()
    for file_no in range(10):
        filename = f"content_{file_no}"
        file = d / filename
        file.write_text(next(fake_content_generator))
        result += [(str(file), filename)]

    return result


@pytest.mark.parametrize(
    "file_count",
    range(1, 10),
    ids=lambda file_count: f"Upload {file_count} files to existing page",
)
def test_upload_files_single_page_config(setup_page, gen_attachments, file_count):
    """Tests uploading files to a page - should work"""
    page_id, config_file = setup_page
    files_to_upload = [_[0] for _ in gen_attachments[:file_count]]
    _, filename = gen_attachments[0]

    result: Result = upload_files(config_file=config_file, other_args=files_to_upload)
    assert result.exit_code == 0
    assert "Uploading the files" in result.stdout
    assert f"\tUploading file {filename}" in result.stdout
    assert f"\tUploaded file {filename}" in result.stdout
    assert "Done uploading files" in result.stdout


def test_upload_files_single_page_does_not_exist(tmp_path, gen_attachments):
    """Tries to upload files to a non-existent page. Checks that it will fail"""
    file_to_upload, filename = gen_attachments[0]
    config_file, config = generate_local_config(tmp_path=tmp_path)
    assert not page_created(
        config.pages[0].page_title
    ), "Page was created when it should not had been"
    result: Result = upload_files(config_file=config_file, other_args=[file_to_upload])
    assert result.exit_code == 0


def test_upload_files_single_page_title_supplied(setup_page, gen_attachments):
    """Runs
    confluence_poster --config <config> --page-title <some page name> post-page --upload-files file1 file2...
    And makes sure the files were attached to the proper page
    """
    page_id, config_file = setup_page
    file_to_upload, filename = gen_attachments[0]

    new_title = next(fake_title_generator)
    # Create the page first
    create_page = run_with_config(
        config_file=config_file,
        pre_args=["--page-title", new_title],
        default_run_cmd=generate_run_cmd(runner, app, default_args=["post-page"]),
        input="Y\nN\nY\n",
    )
    created_page_id = get_page_id_from_stdout(create_page.stdout)
    result: Result = upload_files(
        config_file=config_file,
        other_args=[file_to_upload],
        pre_args=["--page-title", new_title],
    )

    assert result.exit_code == 0
    assert (
        len(
            confluence_instance.get_attachments_from_content(created_page_id)["results"]
        )
        == 1
    )
    assert (
        confluence_instance.get_attachments_from_content(created_page_id)["results"][0][
            "title"
        ]
        == filename
    )
    assert (
        len(confluence_instance.get_attachments_from_content(page_id)["results"]) == 0
    ), "The original page should not have any attachments"


@pytest.fixture(scope="function")
def setup_two_pages(tmp_path, record_pages):
    config_path, config = generate_local_config(tmp_path, pages=2)
    post_page_run_cmd = generate_run_cmd(
        runner=runner, app=app, default_args=["post-page"]
    )
    create_page = partial(run_with_config, default_run_cmd=post_page_run_cmd)
    result = create_page(
        config_file=config_path, record_pages=record_pages, input="Y\nN\nY\nY\nN\nY\n"
    )
    assert result.exit_code == 0
    page_ids = get_pages_ids_from_stdout(result.stdout)
    return config_path, config, page_ids


def test_upload_files_multiple_pages_no_agree(setup_two_pages):
    """Checks that validation will fail if more than 1 page is supplied in the config and user replied 'No'
    to the prompt"""
    two_page_config_file, *_ = setup_two_pages
    result: Result = upload_files(
        config_file=two_page_config_file,
        input="N\n",
        other_args=["some_attachment.txt"],
    )
    assert result.exit_code == 3
    assert "Aborting" in result.stdout


def test_upload_files_multiple_pages_agree(setup_two_pages, gen_attachments):
    """Checks that validation will fail if more than 1 page is supplied in the config. User replied 'Yes'
    to the prompt. Script should upload everything to the first page"""
    two_page_config_file, config, page_ids = setup_two_pages
    file_to_upload, filename = gen_attachments[0]
    result: Result = upload_files(
        config_file=two_page_config_file, input="Y\n", other_args=[file_to_upload]
    )
    assert result.exit_code == 0

    page_one, page_two = sorted(list(page_ids))
    assert (
        len(confluence_instance.get_attachments_from_content(page_one)["results"]) == 1
    )
    assert (
        confluence_instance.get_attachments_from_content(page_one)["results"][0][
            "title"
        ]
        == filename
    )
    assert (
        len(confluence_instance.get_attachments_from_content(page_two)["results"]) == 0
    ), "The second page should not have any attachments"


def test_upload_files_multiple_pages_default(setup_two_pages):
    """Checks that validation will fail if more than 1 page is supplied in the config and user used default reply
    to the prompt"""
    two_page_config_file, *_ = setup_two_pages
    result: Result = upload_files(
        config_file=two_page_config_file, input="\n", other_args=["some_attachment.txt"]
    )
    assert result.exit_code == 3
    assert "Aborting" in result.stdout
