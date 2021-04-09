import typer
from click import Choice
from pathlib import Path
from functools import reduce
from typing import Union, Any, Tuple, FrozenSet, Iterable, Callable
from tomlkit import document, parse, table, dumps
from tomlkit.parser import TOMLDocument
from tomlkit.items import Table
from dataclasses import dataclass
from copy import deepcopy

from confluence_poster.poster_config import AllowedFileFormat


@dataclass
class DialogParameter:
    """This class serves as a wrapper around title(str) with extra parameters to be consumed by the dialog prompt"""

    title: str
    comment: Union[str, None] = None  # for passing a comment
    type: Union[type, None, Choice] = None  # for passing type to input
    required: bool = True
    hide_input: bool = False

    def __eq__(self, other):
        """Method to help looking up members of this class when the dialog runs"""
        if isinstance(other, DialogParameter):
            return self.title == other.title
        elif isinstance(other, str):
            return self.title == other
        else:
            raise ValueError

    def __hash__(self):
        """To be used very carefully"""
        return hash(self.title)

    def __getattr__(self, item):
        """To proxy """

        def _missing(*args, **kwargs):
            method = getattr(self.title, item)
            return method(*args, **kwargs)

        return _missing

    def __str__(self):
        return self.title


def _dialog_prompt(parameter: Union[DialogParameter, str], default_value=None) -> Any:
    """Provides a single prompt of the dialog.

    Special case: if None is returned - then the user skipped this parameter"""
    _default_value = default_value
    if type(parameter) is not DialogParameter:
        # For handling default case without special information
        parameter = DialogParameter(title=parameter)

    message = [f"Please provide a value for {parameter.title}."]
    if parameter.comment is not None:
        message += [f"Comment: {parameter.comment}"]
    if not parameter.required:
        message += ["This parameter is optional. Press [Enter] to skip it."]
        if default_value is None:
            _default_value = ""

    if parameter.hide_input:
        if default_value is not None:
            message += [
                f"Current value is set, but input is hidden, indicating a sensitive field.",
                "Press [Enter] to reuse the current value.",
            ]
        else:
            message += ["This parameter is marked as sensitive, input is hidden"]
    elif default_value is not None:
        message += [f"Current value is {default_value}. Press [Enter] to use it."]

    new_value = typer.prompt(
        text="\n".join(message) + "\nValue",
        default=_default_value,
        type=parameter.type,
        hide_input=parameter.hide_input,
        show_default=not parameter.hide_input,
    )
    if not parameter.required and default_value is None and new_value == "":
        new_value = None

    return new_value


def _get_attribute_by_path(attribute_path: str, config: TOMLDocument) -> Any:
    """Given attribute path like path1.path2.attribute return value of attribute, None if attribute is empty
    or path does not exist"""
    attribute_path = attribute_path.split(".")
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

    def key_walk(d: dict, base_path: str = "") -> str:
        """A generator that traverses into a TOMLDocument, keeping track through base_path"""
        for key in d:
            path = base_path
            if type(d[key]) is Table:
                path += key + "."
                yield from key_walk(d[key], base_path=path)
            else:
                yield path + key

    result = tuple(key_walk(config))
    return result


def _create_or_update_attribute(
    attribute: str, config: TOMLDocument, value: str
) -> TOMLDocument:
    """Given attribute path path1.path2.attribute, do the following:

    1. Traverse the document, creating tables for path1 and path2 if they do not exist. 'path2' would be nested in path1
    2. Set the attribute attribute to the value

    Returns a copy of config with updated value
    """
    *attribute_path, attribute_name = attribute.split(".")
    _config = deepcopy(config)
    caret = _config
    for path_node in attribute_path:  # more clear than a reduce() call
        next_node = caret.get(path_node)
        if next_node is None:
            caret[path_node] = table()
        caret = caret.get(path_node)

    caret[attribute_name] = value
    return parse(dumps(_config))


def print_config_with_hidden_attrs(
    config: TOMLDocument, hidden_attributes: Iterable[Union[str, DialogParameter]]
) -> str:
    """Given a path on the filesystem and a list of hidden attributes, returns content of that file,
    redacting the sensitive fields"""
    _config = deepcopy(config)
    for attribute in hidden_attributes:
        if _get_attribute_by_path(str(attribute), _config) is not None:
            _config = _create_or_update_attribute(
                str(attribute), _config, value="[REDACTED]"
            )

    return dumps(_config)


def config_dialog(
    filename: Union[Path, str],
    attributes: Iterable[Union[str, DialogParameter]],
    config_print_function: Callable = lambda _: print(_),
    incremental: bool = False,
) -> Union[None, bool]:
    """Checks if filename exists and goes through the list of attributes asking the user for the values

    :param filename: filename (path or string) containing the config to be output
    :param attributes: list of parameter paths or DialogParameters to be displayed
    :param config_print_function: function that prints the config file.
    Can be overridden using print_config_file function to preserve list of redacted attributes.
    :param incremental: if set to True - suppresses the prompt to overwrite the file
    """
    if type(filename) is str:
        filename = Path(filename)
    new_config = document()
    if filename.exists():
        typer.echo(f"File {filename} already exists.")
        new_config = parse(filename.read_text())
        if not incremental:
            typer.echo("Current content:")
            typer.echo(config_print_function(new_config))
            if not typer.confirm(f"File {filename} exists. Overwrite?", default=False):
                return  # do not save this config file

    # Process attributes list
    for attr in attributes:
        current_value = _get_attribute_by_path(attr, new_config)
        if current_value is not None:
            if incremental:
                raise Exception(
                    f"Incremental is set, but there is already a value for {attr}. This is probably a bug."
                )
            if not typer.confirm(
                f"Would you like to overwrite current value of {attr}: {current_value}?",
                default=True,
            ):
                continue  # next attribute
        new_value = _dialog_prompt(parameter=attr, default_value=current_value)

        if new_value is not None:
            new_config = _create_or_update_attribute(
                attribute=attr, config=new_config, value=new_value
            )

    typer.echo(f"Config to be saved:")
    typer.echo(config_print_function(new_config))

    save = typer.confirm(
        f"Would you like to save it as {filename}? "
        "The wizard will create all missing parent directories",
        default=True,
    )
    if save:
        typer.echo(f"Saving config as {filename}")
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(dumps(new_config))
        if any([_.hide_input for _ in attributes if isinstance(_, DialogParameter)]):
            typer.echo(
                "Since a sensitive parameter was passed - saving the config file with 600 permissions."
            )
            filename.chmod(0o600)
        return True
    else:
        return False


def get_filled_attributes_from_file(filename: Union[Path, str]) -> FrozenSet[str]:
    if type(filename) is str:
        filename = Path(filename)
    if not filename.exists():
        return frozenset()
    return frozenset(_get_filled_attributes(parse(filename.read_text())))


def _generate_next_page(filename: Union[Path, str]) -> int:
    existing_pages = set(
        map(
            lambda a: a.split(".")[1],
            filter(
                lambda _: _.startswith("pages")
                and not _.startswith("pages.default")
                and not _ == "pages",
                get_filled_attributes_from_file(filename),
            ),
        )
    )
    page_number = 1
    while True:
        if f"page{page_number}" not in existing_pages:
            return page_number
        else:
            page_number = page_number + 1


def generate_page_dialog_params(
    page_no: int,
) -> Tuple[DialogParameter, DialogParameter, DialogParameter, DialogParameter]:
    # noinspection PyUnresolvedReferences
    return (
        DialogParameter(
            title=f"pages.page{page_no}.page_title", comment="The title of the page"
        ),
        DialogParameter(
            title=f"pages.page{page_no}.page_file", comment="File containing page text"
        ),
        DialogParameter(
            title=f"pages.page{page_no}.page_file_format",
            comment="Text format of the page file. None or default - the script will try to guess it at runtime.",
            type=Choice(
                [_[0] for _ in AllowedFileFormat.__members__.items()]
            ),  # making the linter happy, see JetBrains PY-36205
            required=False,
        ),
        DialogParameter(
            title=f"pages.page{page_no}.page_space",
            comment="Key of the space with the page",
            required=False,
        ),
    )


def page_add_dialog(
    filename: Union[Path, str], config_print_function=lambda _: print(_)
) -> bool:
    """Wrapper around config_dialog that generates a new page section"""
    # processes list of pages.page1, pages.page2 to "page1", "page2"
    page_number = _generate_next_page(filename)
    return config_dialog(
        filename,
        attributes=generate_page_dialog_params(page_number),
        config_print_function=config_print_function,
        incremental=True,
    )
