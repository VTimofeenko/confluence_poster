import typer
from typing import Optional, List, Union
from pprint import pprint
from pathlib import Path
from logging import basicConfig, DEBUG
from confluence_poster.poster_config import Config
from atlassian import Confluence
from dataclasses import dataclass


@dataclass
class StateConfig:
    """Holds the shared state between typer commands"""
    force: bool = False
    debug: bool = False
    confluence_instance: Union[None, Confluence] = None
    config: Union[None, Config] = None
    page_title: Union[str, None] = None


app = typer.Typer()
state = StateConfig()


@app.command()
def post_page():
    pass


@app.command()
def validate():
    """Validates the provided settings"""
    pass


@app.command()
def upload_files(files: List[Path]):
    typer.echo("Uploading the files")
    for path in files:
        if path.is_file():
            typer.echo(f"Uploading file {path.name}")
    typer.echo("Done uploading files")


@app.callback()
def main(ctx: typer.Context,
         config: str = typer.Option(default="config.toml", help="The filename of config.json"),
         page_title: Optional[str] = typer.Option(None, help="Override page title from config."
                                                             " Applicable if there is only one page"),
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
    if page_title:
        if len(confluence_config.pages) > 1:
            typer.echo("Page title specified as a parameter but there are more than 1 page in the config. Aborting.")
            raise typer.Exit(1)
        state.page_title = page_title

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


