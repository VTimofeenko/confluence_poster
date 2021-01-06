import typer
import sys
from click import Choice
from typing import Optional, List, Tuple
from pathlib import Path
from logging import basicConfig, DEBUG
from atlassian import Confluence
from atlassian.errors import ApiError
from dataclasses import dataclass, field, astuple
from requests.exceptions import ConnectionError

from confluence_poster.poster_config import Page, AllowedFileFormat
from confluence_poster.config_loader import load_config
from confluence_poster.config_wizard import DialogParameter, generate_page_dialog_params
from confluence_poster.main_helpers import (
    check_last_updated_by,
    PostedPage,
    guess_file_format,
    get_representation_for_format,
    StateConfig,
    get_page_url,
)
from confluence_poster.convert_markdown_utils import post_to_convert_api
from confluence_poster.page_creation_helpers import create_page
from confluence_poster.file_upload_helpers import attach_files_to_page

__version__ = "1.3.0"
default_config_name = "config.toml"


def version_callback(value: bool):
    if value:
        typer.echo(f"Confluence poster version: {__version__}")
        raise typer.Exit()


@dataclass
class Report:
    created_pages: List[Page] = field(default_factory=list)
    updated_pages: List[Page] = field(default_factory=list)
    unprocessed_pages: List[Tuple[Page, str]] = field(default_factory=list)
    confluence_instance: Confluence = None

    def __str__(self) -> str:
        output = ""
        for header, page_list in [
            ("Created pages:", self.created_pages),
            ("Updated pages:", self.updated_pages),
        ]:
            output += header + "\n"
            if page_list:
                for page in page_list:
                    title = page.page_title
                    space = page.page_space
                    output += f"{space}::{title} {get_page_url(title, space, self.confluence_instance)}\n"
            else:
                output += "None\n"
        if self.unprocessed_pages:
            output += "Unprocessed pages:"
            for page, reason in self.unprocessed_pages:
                output += f"{page.page_space}::{page.page_title} Reason: {reason}"

        return output


app = typer.Typer()
state = StateConfig()


@app.command()
def convert_markdown(
    use_confluence_converter: Optional[bool] = typer.Option(
        True,
        "--use-confluence-converter",
        show_default=False,
        help="Use built-in Confluence converter. Note: uses Confluence private API",
    )
):
    """Converts single page text from markdown to html representation (aka "editor"). Prints the converted text.
    Implies running the utility with --quiet."""
    confluence = state.confluence_instance
    if len(state.config.pages) > 1:
        typer.echo(
            "This command supports converting only one page at a time.", err=True
        )
        raise typer.Exit(1)

    if use_confluence_converter:
        typer.echo(
            "Using the converter built into Confluence which is labeled as private API. "
            "Consider using external tool",
            err=True,
        )
        typer.echo(post_to_convert_api(confluence, state.config.pages[0].page_text))
    typer.echo(
        "Submit the converted text using `confluence_poster post-page --file-format html`",
        err=True,
    )


@app.command()
def post_page(
    upload_files: Optional[bool] = typer.Option(
        False, "--upload-files", show_default=False, help="Upload list of files"
    ),
    version_comment: Optional[str] = typer.Option(
        None,
        "--version-comment",
        show_default=False,
        help="Provider version comment.",
    ),
    create_in_space_root: Optional[bool] = typer.Option(
        False,
        "--create-in-space-root",
        help="Create the page in space root",
    ),
    file_format: Optional[AllowedFileFormat] = typer.Option(
        AllowedFileFormat.none,
        "--file-format",
        show_default=False,
        help="File format of the file with the page content. "
        "If provided at runtime - can only be applied to a single page. "
        "If set to 'None'(default) - script will try to guess it during the run.",
    ),
    files: Optional[List[Path]] = typer.Argument(None, help="List of files to upload"),
):
    """Posts the content of the pages."""
    report = Report(confluence_instance=state.confluence_instance)
    confluence = state.confluence_instance
    posted_pages = [PostedPage(*astuple(_)) for _ in state.config.pages]
    target_page = posted_pages[0]

    if len(posted_pages) > 1 and version_comment is not None:
        apply_version_comment_to = typer.prompt(
            text=f"Multiple pages specified. Do you want to apply the comment to [A]ll pages, "
            "[F]irst one or [N]ot apply it?",
            type=Choice(choices=["A", "F", "N"], case_sensitive=False),
            default="A",
        ).lower()
        if apply_version_comment_to == "a":
            for page in posted_pages:
                page.version_comment = version_comment
        elif apply_version_comment_to == "f":
            posted_pages[0].version_comment = version_comment
        else:
            for page in posted_pages:
                page.version_comment = None
    else:
        # set the comment for the single page
        posted_pages[0].version_comment = version_comment

    # file format check
    if len(posted_pages) > 1 and file_format is not AllowedFileFormat.none:
        typer.echo(
            "File format cannot be used for cases when there are more than 1 pages in the config. "
            "Consider adding it to the config file."
        )
        raise typer.Exit(1)

    posted_pages[0].page_file_format = file_format

    if upload_files:
        if len(posted_pages) > 1:
            typer.echo(
                "Upload files are specified, but there are more than 1 pages in the config."
            )
            if typer.confirm(
                f"Continue by attaching all files to the first page, '{target_page.page_title}'? ('N') to abort",
                default=False,
            ):
                pass
            else:
                typer.echo("Aborting.")
                raise typer.Exit(3)

    for page in posted_pages:
        if page.page_file_format is AllowedFileFormat.none:
            state.print_function(
                f"File format for page {page.page_title} not specified. Trying to determine it..."
            )
            try:
                guessed_format = guess_file_format(page.page_file)
            except ValueError as e:
                typer.echo(
                    "Could not guess the file format. Consider specifying it manually. "
                    "See --help for information",
                    err=True,
                )
                raise e
            page.page_file_format = guessed_format

        state.print_function(f"Looking for page '{page.page_title}'")
        if page_id := confluence.get_page_id(
            space=page.page_space, title=page.page_title
        ):
            # Page exists
            state.print_function(f"Found page id #{page_id}")
            page.page_id = page_id

            # If --force is supplied - we do not really care about who edited the page last
            if not (state.force or page.force_overwrite):
                updated_by_author, page_last_updated_by = check_last_updated_by(
                    page_id=page_id,
                    username_to_check=state.config.author,
                    confluence_instance=confluence,
                )
                if not updated_by_author:
                    state.print_function(
                        f"Flag 'force' is not set and last author of page '{page.page_title}'"
                        f" is {page_last_updated_by}, not {state.config.author}. Skipping page"
                    )
                    continue
            else:
                if state.force:
                    state.print_function("Flag 'force' set globally.")
                elif page.force_overwrite:
                    state.print_function("Flag 'force overwrite' set on the page.")
                state.print_function("Author name check skipped.")

            state.print_function(f"Updating page #{page_id}")
            confluence.update_existing_page(
                page_id=page_id,
                title=page.page_title,
                body=page.page_text,
                representation=get_representation_for_format(
                    page.page_file_format
                ).value,
                minor_edit=state.minor_edit,
                version_comment=page.version_comment,
            )
            report.updated_pages += [page]
        else:
            state.print_function(
                f"Could not find page '{page.page_title}' in space '{page.page_space}'"
            )
            if page_created := create_page(
                page=page, state=state, create_in_root=create_in_space_root
            ):
                report.created_pages += [page]
                if version_comment:
                    state.print_function(
                        "Page was created, but Confluence API does not support setting the version comment for"
                        " page creation. The comment was not provided."
                    )
                page.page_id = page_created.page_id
            else:
                typer.echo(f"Not creating page '{page.page_title}'")
                report.unprocessed_pages += [(page, page_created.comment)]

        if upload_files and target_page.page_id is not None:
            attach_files_to_page(page=target_page, files=files, state=state)

    typer.echo("Finished processing pages")

    if state.print_report:
        typer.echo(report)


@app.command()
def validate(
    online: Optional[bool] = typer.Option(
        False,
        "--online",
        show_default=False,
        help="Test the provided authentication settings on the actual"
        " instance of confluence.",
    )
):
    """Validates the provided settings. If 'online' is true - tries to fetch the space from the config using the
    supplied credentials."""
    if online:
        state.print_function(
            "Validating settings against the Confluence instance from config"
        )
        try:
            space_key = state.config.pages[0].page_space
            state.print_function(f"Trying to get {space_key}...")
            space_id = state.confluence_instance.get_space(space_key).get("id")
        except ConnectionError:
            state.print_function(
                f"Could not connect to {state.config.auth.url}. Make sure it is correct"
            )
            raise typer.Abort(1)
        except ApiError as e:
            state.print_function(f"Got an API error, details: {e.reason}")
            raise typer.Abort(1)
        else:
            state.print_function(f"Got space id #{space_id}.")
    state.print_function("Validation successful")
    return


@app.command()
def create_config(
    local_only: Optional[bool] = typer.Option(
        False, "--local-only", help="Create config only in the local folder"
    ),
    home_only: Optional[bool] = typer.Option(
        False, "--home-only", help="Create config only in the $XDG_CONFIG_HOME"
    ),
):
    """Runs configuration wizard. The wizard guides through setting up values for config."""
    import xdg
    from confluence_poster.config_wizard import (
        config_dialog,
        get_filled_attributes_from_file,
        print_config_with_hidden_attrs,
        page_add_dialog,
    )
    from functools import partial

    home_config_location = xdg.xdg_config_home() / "confluence_poster/config.toml"

    all_params = (
        DialogParameter(
            "author",
            comment="If the page was not updated by the username specified here, throw an error."
            "\nIf this setting is omitted - username from auth section "
            "is used for checks",
            required=False,
        ),
        # auth:
        DialogParameter("auth.confluence_url", comment="URL of confluence instance"),
        DialogParameter(
            "auth.username", comment="Username for authentication in Confluence"
        ),
        DialogParameter(
            "auth.password",
            comment="Password for authentication. May be supplied through runtime option or "
            "environment",
            required=False,
            hide_input=True,
        ),
        DialogParameter(
            "auth.is_cloud",
            comment="Whether the confluence instance is a cloud one",
            type=bool,
        ),
        # pages:
        DialogParameter(
            "pages.default.page_space",
            comment="Space key (e.g. LOC for 'local-dev' space). If defined here - will be used "
            "if a page does not redefine it",
            required=False,
        ),
    ) + generate_page_dialog_params(1)
    home_only_params = (
        "author",
        "auth.confluence_url",
        "auth.username",
        "auth.password",
        "auth.is_cloud",
    )
    # To hide password in prompts
    _print_config_file = partial(
        print_config_with_hidden_attrs, hidden_attributes=["auth.password"]
    )
    config_dialog = partial(config_dialog, config_print_function=_print_config_file)
    page_add_dialog = partial(page_add_dialog, config_print_function=_print_config_file)

    # Initial prompt
    state.print_function("Starting config wizard.")
    state.print_function(
        "This wizard will guide you through creating the configuration files."
    )
    answer = ""
    if not any([local_only, home_only]):
        state.print_function(
            "Since neither '--local-only' nor '--home-only' were specified, wizard will guide you through creating "
            f"config files in {home_config_location.parent}(XDG_CONFIG_HOME) and {Path.cwd()}(local directory)"
        )

        answer = typer.prompt(
            f"Create config in {home_config_location.parent}? [Y/n/q]"
            "\n* 'n' skips to config in the local directory"
            "\n* 'q' will exit the wizard\n",
            type=str,
            default="y",
        ).lower()

        if answer == "q":
            raise typer.Exit()

    if (answer == "y" and not local_only) or home_only:
        # Create config in home
        while True:
            dialog_result = config_dialog(
                filename=home_config_location,
                attributes=[_ for _ in all_params if _ in home_only_params],
            )
            if dialog_result is None or dialog_result:
                # None means the user does not want to overwrite the file
                break

    if home_only:
        # If --home-only is specified - no need to create another one in local folder
        state.print_function(
            "--home-only specified, not attempting to create any more configs."
        )
        raise typer.Exit()

    if not local_only:
        # If local-only is passed - no need to ask for confirmation of creating a local only config
        local_answer = typer.confirm(
            f"Proceed to create config in {Path.cwd()}?", default=True
        )
        if not local_answer:
            typer.echo("Exiting.")
            raise typer.Exit()

    # Create config in current working directory
    state.print_function("Creating config in local directory.")
    local_config_name = typer.prompt(
        "Please provide the name of local config", type=str, default=default_config_name
    )

    home_parameters = get_filled_attributes_from_file(home_config_location)
    local_config_parameters = [_ for _ in all_params if _ not in home_parameters]

    while True:
        dialog_result = config_dialog(
            filename=Path.cwd() / local_config_name, attributes=local_config_parameters
        )
        if dialog_result is None or dialog_result:
            # None means the user does not want to overwrite the file
            break

    while typer.confirm("Add more pages?", default=False):
        page_add_dialog(Path.cwd() / local_config_name)

    typer.echo(
        "Configuration wizard finished. Consider running the `validate` command to check the generated config"
    )


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", help="Show version and exit", callback=version_callback
    ),
    config: Path = typer.Option(
        default=default_config_name,
        help="The file containing configuration. "
        f"If not specified - {default_config_name} from the same directory is used",
    ),
    page_title: Optional[str] = typer.Option(
        None,
        help="Override page title from config."
        " Applicable if there is only one page.",
    ),
    parent_page_title: Optional[str] = typer.Option(
        None,
        help="Provide a parent title to search for."
        " Applicable if there is only one page.",
    ),
    page_file: Optional[Path] = typer.Option(
        None,
        help="Provide the path to the file containing page text. Allows passing '-' to read from stdin",
    ),
    password: Optional[str] = typer.Option(
        None, help="Supply the password in command line.", envvar="CONFLUENCE_PASSWORD"
    ),
    force: Optional[bool] = typer.Option(
        False,
        "--force",
        show_default=False,
        help="Force overwrite the pages. Skips all checks for different author of the updated page. "
        "To set for individual pages you can specify field 'force_overwrite' in config",
    ),
    force_create: Optional[bool] = typer.Option(
        False,
        "--force-create",
        show_default=False,
        help="Disable prompts to create pages. "
        "Script could still prompt for a parent page.",
    ),
    minor_edit: Optional[bool] = typer.Option(
        False,
        "--minor-edit",
        show_default=False,
        help="Do not notify watchers of pages updates. " "Not enabled by default.",
    ),
    report: Optional[bool] = typer.Option(
        False,
        "--report",
        show_default=False,
        help="Print report at the end of the run. " "Not enabled by default.",
    ),
    debug: Optional[bool] = typer.Option(
        False,
        "--debug",
        show_default=False,
        help="Enable debug logging. " "Not enabled by default.",
    ),
    quiet: Optional[bool] = typer.Option(
        False,
        "--quiet",
        show_default=False,
        help="Suppresses certain output.",
    ),
):
    """Supplementary script for writing confluence wiki articles in
    vim. Uses information from the config to post the article content to confluence.
    """
    if ctx.invoked_subcommand == "convert-markdown":
        quiet = True

    if page_file == "-":
        quiet = True
        state.filter_mode = True
        if ctx.invoked_subcommand not in {"convert-markdown", "post-page"}:
            typer.echo(
                f"Invoked command, {ctx.invoked_subcommand} is not compatible with reading page text from stdin",
                err=True,
            )

    state.quiet = quiet

    state.print_function("Starting up confluence_poster")

    if debug:
        from pprint import pprint

        typer.echo("Set options:")
        state.debug = True
        typer.echo(pprint(locals()))
        # Set global debug to true, for other modules
        basicConfig(level=DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    else:
        state.debug = False

    if (
        ctx.invoked_subcommand != "create-config"
    ):  # no need to validate or load the config if we're creating it
        state.force = force
        state.force_create = force_create
        state.print_report = report
        state.minor_edit = minor_edit

        state.print_function("Reading config")
        try:
            confluence_config = load_config(config)
        except FileNotFoundError as e:
            typer.echo("Config file not found. Consider running `create-config`")
            raise e
        state.config = confluence_config

        # Check that the parameters are not used with more than 1 page in the config
        if page_title or parent_page_title or page_file:
            if len(confluence_config.pages) > 1:
                typer.echo(
                    "Page title, parent page title or page file specified as a parameter "
                    "but there are more than 1 page in the config.\n"
                    "These parameters are intended to be used with only one page.\n"
                    "Please specify them in the config.\n"
                    "Aborting.",
                    err=True,
                )
                raise typer.Exit(1)
            if page_title:
                state.config.pages[0].page_title = page_title
            if parent_page_title:
                state.config.pages[0].parent_page_title = parent_page_title
            if page_file:
                if page_file == "-":
                    state.config.pages[0].page_text = sys.stdin.read()
                else:
                    state.config.pages[0].page_file = page_file

        # Validate password
        try:
            _password = next(
                _ for _ in [password, confluence_config.auth.password] if _ is not None
            )
        except StopIteration:
            typer.echo(
                "Password is not specified in environment, parameter or the config. Aborting",
                err=True,
            )
            raise typer.Exit(1)

        # set API version
        if confluence_config.auth.is_cloud:
            api_version = "cloud"
        else:
            api_version = "latest"

        state.confluence_instance = Confluence(
            url=confluence_config.auth.url,
            username=confluence_config.auth.username,
            password=_password,
            api_version=api_version,
        )
