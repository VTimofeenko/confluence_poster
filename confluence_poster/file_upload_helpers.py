from typing import Iterable
from pathlib import Path

from confluence_poster.main_helpers import StateConfig, PostedPage


def attach_files_to_page(
    page: PostedPage, files: Iterable[Path], state: StateConfig
) -> None:
    echo = state.print_function
    always_echo = state.always_print_function

    always_echo("Uploading the files")
    for path in files:
        if path.is_file():
            echo(f"\tUploading file {path.name}...")
            state.confluence_instance.attach_file(
                str(path), name=path.name, page_id=str(page.page_id)
            )
            echo(f"\tUploaded file {path.name}.")
    always_echo("Done uploading files")
