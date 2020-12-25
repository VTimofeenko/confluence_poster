import typer
from pathlib import Path
from functools import reduce
import toml
from typing import List, Dict, Union, Any, Tuple
from tomlkit import document, parse, table, dumps
from tomlkit.parser import TOMLDocument
from tomlkit.items import Table
from dataclasses import dataclass
from .poster_config import Auth, Page
from copy import deepcopy


def _get_attribute_by_path(attribute_path: str, config: TOMLDocument) -> Any:
    """Given attribute path like path1.path2.attribute return value of attribute, None if attribute is empty
     or path does not exist"""
    attribute_path = attribute_path.split('.')
    try:
        return reduce(lambda caret, key: caret.get(key, None), attribute_path, config)
    except AttributeError:  # for cases when we try to call get() on None
        return None


def _get_filled_attributes(config: TOMLDocument) -> Tuple[str]:
    """For a config like this:

    foo = 'bar'
    [table]
    foo = 'bar'
    [table.child]
    foo = 'bar'

    produces (foo, table.foo, table.child.foo)
    """
    def key_walk(d: dict, base_path: str = '') -> str:
        """A generator that traverses into a TOMLDocument, keeping track through base_path"""
        for key in d:
            path = base_path
            if type(d[key]) is Table:
                path += key + '.'
                yield from key_walk(d[key], base_path=path)
            else:
                yield path + key
    result = tuple(key_walk(config))
    return result


def _create_or_update_attribute(attribute: str, config: TOMLDocument, value: str) -> TOMLDocument:
    """Given attribute path path1.path2.attribute, do the following:

    1. Traverse the document, creating tables for path1 and path2 if they do not exist. 'path2' would be nested in path1
    2. Set the attribute attribute to the value

    Returns a copy of config with updated value
    """
    *attribute_path, attribute_name = attribute.split('.')
    _config = deepcopy(config)  # TODO: check if needed
    caret = _config
    for path_node in attribute_path:  # more clear than a reduce() call
        next_node = caret.get(path_node)
        if next_node is None:
            caret[path_node] = table()
        caret = caret.get(path_node)

    caret[attribute_name] = value
    # return _config  # TODO: ugly. Otherwise _config dictionary mutates into {'foz': 'baz'} state
    return parse(dumps(_config))


app = typer.Typer()


@app.command()
def config_dialog(filename: Union[Path, str], attributes: List[str]) -> Union[None, bool]:
    """Checks if filename exists and goes through the list of attributes asking the user for the values
    """
    if type(filename) is str:
        filename = Path(filename)
    new_config = document()
    if filename.exists():
        typer.echo(f"File {filename} already exists.")
        typer.echo("Current content:")
        typer.echo((content := filename.read_text()))
        if not typer.confirm(f"File {filename} exists. Overwrite?", default=False):
            return  # do not save this config file

        new_config = parse(content)

    # Process attributes list
    for attr in attributes:
        current_value = _get_attribute_by_path(attr, new_config)
        message = f"Please provide a value for {attr}"
        if current_value is not None:
            if not typer.confirm(f"Would you like to overwrite current value of {attr}: {current_value}?",
                                 default=True):
                continue  # next attribute
            message += f". Current value is: {current_value}. Hit [Enter] to use the current value."
            new_value = typer.prompt(text=message, default=current_value)
        else:
            new_value = typer.prompt(text=message)

        new_config = _create_or_update_attribute(attribute=attr, config=new_config, value=new_value)

    typer.echo(f"Config to be saved in {filename}:")
    typer.echo(message=dumps(new_config))

    save = typer.confirm("Would you like to save it?", default=True)
    if save:
        typer.echo(f"Saving config as {filename}")
        filename.write_text(dumps(new_config))
        return True
    else:
        return False
