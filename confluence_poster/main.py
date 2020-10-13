import typer
from typing import Optional, List, Union
from pathlib import Path
from logging import basicConfig, DEBUG
from confluence_poster.poster_config import Config
from atlassian import Confluence
from atlassian.errors import ApiError
from dataclasses import dataclass, field
from requests.exceptions import ConnectionError


@dataclass
class StateConfig:
    """Holds the shared state between typer commands"""
    force: bool = False
    debug: bool = False
    confluence_instance: Union[None, Confluence] = None
    config: Union[None, Config] = None
    created_pages: List[int] = field(default_factory=list)


app = typer.Typer()
state = StateConfig()


@app.command()
def post_page():
    confluence = state.confluence_instance
    for page in state.config.pages:
        typer.echo(f"Looking for page '{page.page_name}'")
        if page_id := confluence.get_page_id(space=page.page_space, title=page.page_name):
            # Page exists
            typer.echo(f"Found page id #{page_id}")

            # If --force is supplied - we do not really care about who edited the page last
            if not state.force:
                page_last_updated_by = confluence.get_page_by_id(page_id, expand='version')['version']['by']
                if confluence.api_version == "cloud":
                    page_last_updated_by = page_last_updated_by['email']
                else:
                    page_last_updated_by = page_last_updated_by['username']
                if page_last_updated_by != state.config.author:
                    typer.echo(f"Flag 'force' is not set and last author of page '{page.page_name}'"
                               f" is {page_last_updated_by}, not {state.config.author}. Skipping page")
                    continue
            with open(page.page_file, 'r') as _:
                typer.echo(f"Updating page #{page_id}")
                confluence.update_existing_page(page_id=page_id, title=page.page_name, body=_.read(),
                                                representation='wiki')
        else:
            # Page does not exist. Confluence API reports it itself
            typer.echo("Page not found")
            parent_id = None
            if typer.confirm("Should it be created?", default=True):
                while typer.confirm(f"Should the script look for a parent in space {page.page_space}?"
                                    f" (N to be prompted to create the page in the root)"):
                    parent_name = typer.prompt("Which page should the script look for?")
                    if parent_page := confluence.get_page_by_title(space=page.page_space, title=parent_name,
                                                                   expand=''):
                        # according to Atlassian REST API reference, '_links' is a legitimate way to access links
                        parent_link = confluence.url + parent_page["_links"]["webui"]
                        if typer.confirm(f"Found page #{parent_page['id']}, called {parent_name}. URL is:\n"
                                         f"{parent_link}\n"
                                         f"Proceed to create?"):
                            parent_id = parent_page["id"]
                            break

                else:
                    # If parent_id stays None, page will be created in the root
                    if not typer.confirm(f"Create the page in the root of {page.page_space}? N will skip the page"):
                        continue
                with open(page.page_file, 'r') as _:
                    typer.echo("Creating page")

                    response = confluence.create_page(space=page.page_space, title=page.page_name, body=_.read(),
                                                      parent_id=parent_id,
                                                      representation='wiki')
                    page_id = response['id']
                    typer.echo(f"Created page #{page_id} in space {page.page_space} called '{page.page_name}'")
                    state.created_pages.append(int(page_id))
            else:
                typer.echo(f"Not creating page '{page.page_name}'")
    typer.echo("Finished processing pages")


@app.command()
def validate(online: Optional[bool] = typer.Option(default=False,
                                                   help="Test the provided authentication settings on the actual"
                                                        " instance of confluence")):
    """Validates the provided settings. If 'online' is true - tries to fetch the space from the config"""
    if online:
        typer.echo("Validating settings against the Confluence instance from config")
        try:
            space_key = state.config.pages[0].page_space
            typer.echo(f"Trying to get {space_key}...")
            space_id = state.confluence_instance.get_space(space_key)
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
def upload_files(files: List[Path]):
    typer.echo("Uploading the files")
    for path in files:
        if path.is_file():
            typer.echo(f"Uploading file {path.name}")
    typer.echo("Done uploading files")


@app.callback()
def main(config: str = typer.Option(default="config.toml", help="The filename of config.json"),
         page_name: Optional[str] = typer.Option(None, help="Override page title from config."
                                                            "Applicable if there is only one page"),
         password: Optional[str] = typer.Option(None,
                                                help="Supply the password in command line",
                                                envvar="CONFLUENCE_PASSWORD"),
         force: Optional[bool] = typer.Option(default=False, help="Force overwrite the pages"),
         debug: Optional[bool] = typer.Option(default=False, help="Enable debug logging")):
    """ Supplementary script for writing confluence wiki articles in
    vim. Uses information from config.json to post the article content to confluence.
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
    if force:
        state.force = True

    typer.echo("Reading config")
    confluence_config = Config(config)
    state.config = confluence_config

    # Check that the page_title is not used with more than 1 page in the config
    if page_name:
        if len(confluence_config.pages) > 1:
            typer.echo("Page title specified as a parameter but there are more than 1 page in the config. Aborting.")
            raise typer.Exit(1)
        state.config.pages[0].page_name = page_name

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
