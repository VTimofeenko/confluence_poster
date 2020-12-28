import typer
from typing import Optional, List, Union, Tuple
from pathlib import Path
from logging import basicConfig, DEBUG
from confluence_poster.poster_config import Config, Page
from confluence_poster.config_loader import load_config
from atlassian import Confluence
from atlassian.errors import ApiError
from dataclasses import dataclass, field
from requests.exceptions import ConnectionError

__version__ = '1.1.0'
default_config_name = 'config.toml'


def version_callback(value: bool):
    if value:
        typer.echo(f"Confluence poster version: {__version__}")
        raise typer.Exit()


def get_page_url(page_title: str, space: str, confluence: Confluence) -> Union[str, None]:
    """Retrieves page URL"""
    if page := confluence.get_page_by_title(space=space, title=page_title,
                                            expand=''):
        # according to Atlassian REST API reference, '_links' is a legitimate way to access links
        page_link = confluence.url + page["_links"]["webui"]
        return page_link
    else:
        return None


@dataclass
class StateConfig:
    """Holds the shared state between typer commands"""
    force: bool = False
    debug: bool = False
    confluence_instance: Union[None, Confluence] = None
    config: Union[None, Config] = None
    minor_edit: bool = False
    print_report: bool = False
    force_create: bool = False
    created_pages: List[int] = field(default_factory=list)


@dataclass
class Report:
    created_pages: List[Page] = field(default_factory=list)
    updated_pages: List[Page] = field(default_factory=list)
    unprocessed_pages: List[Tuple[Page, str]] = field(default_factory=list)
    confluence_instance: Confluence = None

    def __str__(self) -> str:
        output = ''
        for header, page_list in [("Created pages:", self.created_pages),
                                  ("Updated pages:", self.updated_pages)]:
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


def create_page(page: Page, confluence: Confluence) -> (bool, Union[int, None]):
    """Handles user input for page creation. Returns True and page_id if the page is created."""

    def find_parent(_parent_name: str, space: str) -> Union[int, None]:
        """Helper function to locate the parent page. Returns page id. Returns None if page is not found"""
        typer.echo(f"Looking for the parent page with title {_parent_name}")
        if parent_page := confluence.get_page_by_title(space=space, title=_parent_name,
                                                       expand=''):
            # according to Atlassian REST API reference, '_links' is a legitimate way to access links
            parent_link = get_page_url(_parent_name, space, confluence)
            _parent_id = parent_page["id"]
            typer.echo(f"Found page #{_parent_id}, called {_parent_name}. URL is:\n{parent_link}")
            return _parent_id
        else:
            typer.echo(f"Parent page '{_parent_name}' not found")
            return None

    # Page does not exist. Confluence API reports it itself
    typer.echo(f"Page '{page.page_title}' not found")
    parent_id = None
    if state.force_create or typer.confirm("Should it be created?", default=True):
        if not page.parent_page_title:
            while typer.confirm(f"Should the script look for a parent in space {page.page_space}?"
                                f" (N to be prompted to create the page in the space root)"):
                parent_name = typer.prompt("Which page should the script look for?")
                if parent_id := find_parent(parent_name, page.page_space):
                    if typer.confirm(f"Proceed to create?"):
                        break
                    else:
                        return False, None
            else:
                # If _parent_id stays None, page will be created in the root
                if not typer.confirm(f"Create the page in the root of {page.page_space}? N will skip the page"):
                    return False, None
        else:
            typer.echo(f"Creating under the specified parent page {page.parent_page_title}")
            parent_id = find_parent(page.parent_page_title, page.page_space)
            if parent_id is None:
                typer.echo(f"Parent page '{page.parent_page_title}' not found in space '{page.page_space}'. "
                           f"Skipping page.")
                return False, None

        with open(page.page_file, 'r') as _:
            typer.echo("Creating page")

            response = confluence.create_page(space=page.page_space, title=page.page_title, body=_.read(),
                                              parent_id=parent_id,
                                              representation='wiki')
            page_id = response['id']
            typer.echo(f"Created page #{page_id} in space {page.page_space} called '{page.page_title}'")
            return True, page_id
    else:
        return False, None


app = typer.Typer()
state = StateConfig()


@app.command()
def post_page(upload_files: Optional[List[Path]] = typer.Option(default=None,
                                                                help="Files to upload as attachments to page.")):
    """Posts the content of the pages."""
    report = Report(confluence_instance=state.confluence_instance)
    confluence = state.confluence_instance
    target_page = state.config.pages[0]

    if upload_files:
        if len(state.config.pages) > 1:
            typer.echo('Upload files are specified, but there are more than 1 pages in the config.')
            if typer.confirm(f"Continue by attaching all files to the first page, '{target_page.page_title}'?",
                             default=False):
                pass
            else:
                typer.echo("Aborting.")
                raise typer.Exit(1)

    for page in state.config.pages:
        typer.echo(f"Looking for page '{page.page_title}'")
        if page_id := confluence.get_page_id(space=page.page_space, title=page.page_title):
            # Page exists
            typer.echo(f"Found page id #{page_id}")

            # If --force is supplied - we do not really care about who edited the page last
            if not state.force:
                page_last_updated_by = confluence.get_page_by_id(page_id, expand='version')['version']['by']
                if confluence.api_version == "cloud":
                    page_last_updated_by = page_last_updated_by['email']  # pragma: no cover
                else:
                    page_last_updated_by = page_last_updated_by['username']
                if page_last_updated_by != state.config.author:
                    typer.echo(f"Flag 'force' is not set and last author of page '{page.page_title}'"
                               f" is {page_last_updated_by}, not {state.config.author}. Skipping page")
                    continue
            with open(page.page_file, 'r') as _:
                typer.echo(f"Updating page #{page_id}")
                confluence.update_existing_page(page_id=page_id, title=page.page_title, body=_.read(),
                                                representation='wiki', minor_edit=state.minor_edit)
                report.updated_pages += [page]
        else:
            page_was_created, page_id = create_page(page=page, confluence=confluence)
            if page_was_created:
                report.created_pages += [page]
            else:
                typer.echo(f"Not creating page '{page.page_title}'")
                report.unprocessed_pages += [(page, "User cancelled creation when prompted")]

        if page_id and upload_files:
            typer.echo("Uploading the files")
            if page == target_page:
                for path in upload_files:
                    if path.is_file():
                        typer.echo(f"\tUploading file {path.name}")
                        state.confluence_instance.attach_file(str(path),
                                                              name=path.name,
                                                              page_id=page_id)
                        typer.echo(f"\tSubmitted file {path.name}")
                typer.echo("Done uploading files")

    typer.echo("Finished processing pages")

    if state.print_report:
        typer.echo(report)


@app.command()
def validate(online: Optional[bool] = typer.Option(False,
                                                   "--online",
                                                   show_default=False,
                                                   help="Test the provided authentication settings on the actual"
                                                        " instance of confluence.")):
    """Validates the provided settings. If 'online' is true - tries to fetch the space from the config using the
    supplied credentials."""
    if online:
        typer.echo("Validating settings against the Confluence instance from config")
        try:
            space_key = state.config.pages[0].page_space
            typer.echo(f"Trying to get {space_key}...")
            space_id = state.confluence_instance.get_space(space_key).get('id')
        except ConnectionError:
            typer.echo(f"Could not connect to {state.config.auth.url}. Make sure it is correct")
            raise typer.Abort(1)
        except ApiError as e:
            typer.echo(f"Got an API error, details: {e.reason}")
            raise typer.Abort(1)
        else:
            typer.echo(f"Got space id #{space_id}.")
    typer.echo("Validation successful")
    return


@app.command()
def create_config(local_only: Optional[bool] = typer.Option(False,
                                                            "--local-only",
                                                            help="Create config only in the local folder"),
                  home_only: Optional[bool] = typer.Option(False,
                                                           "--home-only",
                                                           help="Create config only in the $XDG_CONFIG_HOME")):
    import xdg
    from confluence_poster.config_wizard import config_dialog, get_filled_attributes_from_file

    home_config_location = xdg.xdg_config_home() / 'confluence_poster/config.toml'

    all_params = ('author',
                  # pages:
                  'pages.default.page_space',
                  'pages.page1.page_title',
                  'pages.page1.page_file',
                  'pages.page1.page_space',
                  # auth:
                  'auth.confluence_url',
                  'auth.username',
                  'auth.password',
                  'auth.is_cloud')
    home_only_params = ('author', 'auth.confluence_url', 'auth.username', 'auth.password', 'auth.is_cloud')

    # Initial prompt
    typer.echo("Starting config wizard.")
    typer.echo("This wizard will guide you through creating the configuration files.")
    answer = ''
    if not any([local_only, home_only]):
        typer.echo("Since neither --local-only nor --home-only were specified, wizard will guide you through creating "
                   f"configs in {xdg.xdg_config_home()} and {Path.cwd()}")

        answer = typer.prompt(f"Create config in {xdg.xdg_config_home()}? [Y/n/q]"
                              "\n* 'n' skips to config in the local directory"
                              "\n* 'q' will exit the wizard\n",
                              type=str,
                              default='y').lower()

        if answer == 'q':
            raise typer.Exit()

    if answer == 'y' and not local_only:
        # Create config in home
        config_dialog(filename=home_config_location,
                      attributes=home_only_params)
        # TODO: password to hidden input
        # TODO: is_cloud boolean
        # TODO: handle returns of config_dialog
    elif home_only:
        # If --home-only is specified - no need to create another one in local folder
        typer.echo("--home-only specified, not attempting to create any more configs.")
        raise typer.Exit()

    if not local_only:
        # If local-only is passed - no need to ask for confirmation of creating a local only config
        local_answer = typer.confirm(f"Proceed to create config in {Path.cwd()}?",
                                     default=True)
        if not local_answer:
            typer.echo("Exiting.")
            raise typer.Exit()

    # Create config in current working directory
    typer.echo("Creating config in local directory.")
    local_config_name = typer.prompt("Please provide the name of local config",
                                     type=str,
                                     default=default_config_name)

    home_parameters = get_filled_attributes_from_file(home_config_location)
    local_config_parameters = [_ for _ in all_params if _ not in home_parameters]

    config_dialog(filename=Path.cwd() / local_config_name,
                  attributes=local_config_parameters)


@app.callback()
def main(ctx: typer.Context,
         version: Optional[bool] = typer.Option(None,
                                                "--version",
                                                help="Show version and exit",
                                                callback=version_callback),
         config: Path = typer.Option(default=default_config_name,
                                     help="The file containing configuration. "
                                          f"If not specified - {default_config_name} from the same directory is used"),
         page_title: Optional[str] = typer.Option(None, help="Override page title from config."
                                                             " Applicable if there is only one page."),
         parent_page_title: Optional[str] = typer.Option(None, help="Provide a parent title to search for."
                                                                    " Applicable if there is only one page."),
         password: Optional[str] = typer.Option(None,
                                                help="Supply the password in command line.",
                                                envvar="CONFLUENCE_PASSWORD"),
         force: Optional[bool] = typer.Option(False,
                                              "--force",
                                              show_default=False,
                                              help="Force overwrite the pages."
                                                   " Applicable if the author is different."),
         force_create: Optional[bool] = typer.Option(False,
                                                     "--force-create",
                                                     show_default=False,
                                                     help="Disable prompts to create pages. "
                                                          "Script could still prompt for a parent page."),
         minor_edit: Optional[bool] = typer.Option(False,
                                                   "--minor-edit",
                                                   show_default=False,
                                                   help="Do not notify watchers of pages updates. "
                                                        "Not enabled by default."),
         report: Optional[bool] = typer.Option(False,
                                               '--report',
                                               show_default=False,
                                               help="Print report at the end of the run. "
                                                    "Not enabled by default."),
         debug: Optional[bool] = typer.Option(False,
                                              '--debug',
                                              show_default=False,
                                              help="Enable debug logging. "
                                                   "Not enabled by default.")):
    """Supplementary script for writing confluence wiki articles in
    vim. Uses information from the config to post the article content to confluence.
    """
    typer.echo("Starting up confluence_poster")
    if debug:
        from pprint import pprint
        typer.echo("Set options:")
        state.debug = True
        typer.echo(pprint(locals()))
        # Set global debug to true, for other modules
        basicConfig(level=DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')
    else:
        state.debug = False

    if ctx.invoked_subcommand != 'create-config':  # no need to validate or load the config if we're loading it
        state.force = force
        state.force_create = force_create
        state.print_report = report
        state.minor_edit = minor_edit

        typer.echo("Reading config")
        confluence_config = load_config(config)
        state.config = confluence_config

        # Check that the parameters are not used with more than 1 page in the config
        if page_title or parent_page_title:
            if len(confluence_config.pages) > 1:
                typer.echo("Page title specified as a parameter but there are more than 1 page in the config. "
                           "Aborting.")
                raise typer.Exit(1)
            if page_title:
                state.config.pages[0].page_title = page_title
            if parent_page_title:
                state.config.pages[0].parent_page_title = parent_page_title

        # Validate password
        try:
            _password = next(_ for _ in [password, confluence_config.auth.password] if _ is not None)
        except StopIteration:
            typer.echo("Password is not specified in environment, parameter or the config. Aborting")
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
            api_version=api_version
        )
    else:
        typer.echo("Starting config wizard")
