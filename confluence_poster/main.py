import typer
from typing import Optional, List, Union
from pathlib import Path
from logging import basicConfig, DEBUG
from confluence_poster.poster_config import Config
from atlassian import Confluence
from atlassian.errors import ApiError
from dataclasses import dataclass
from requests.exceptions import ConnectionError


@dataclass
class StateConfig:
    """Holds the shared state between typer commands"""
    force: bool = False
    debug: bool = False
    confluence_instance: Union[None, Confluence] = None
    config: Union[None, Config] = None


app = typer.Typer()
state = StateConfig()


@app.command()
def post_page():
    pass


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
        except ConnectionError as e:
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
