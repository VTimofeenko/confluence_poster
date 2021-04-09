from tomlkit import parse
import io
from pathlib import Path

# noinspection PyProtectedMember
from confluence_poster.config_wizard import (
    _create_or_update_attribute as create_update_attr,
)

# noinspection PyProtectedMember
from confluence_poster.config_wizard import (
    _get_attribute_by_path as get_attribute_by_path,
)

# noinspection PyProtectedMember
from confluence_poster.config_wizard import (
    _get_filled_attributes as get_filled_attributes,
)

# noinspection PyProtectedMember
from confluence_poster.config_wizard import _dialog_prompt, DialogParameter

# noinspection PyProtectedMember
from confluence_poster.config_wizard import _generate_next_page as generate_next_page
from confluence_poster.config_wizard import get_filled_attributes_from_file
import pytest
from itertools import product

pytestmark = pytest.mark.offline

document = """root_foo = 'root_bar'
control_value = 'value'  # To make sure it's not touched
[parent]
parent_foo = 'parent_bar'  # String
[parent.child]
child_foo = 'child_bar'"""
source_config = parse(document)


@pytest.fixture()
def create_config_file(tmp_path) -> Path:
    config = tmp_path / "config.toml"
    config.write_text(document)
    return config


@pytest.mark.parametrize(
    "path",
    list(
        product(
            ["root", "parent", "parent.child", "parent.child.nonexistent_child"],
            ["foo", "foz"],
        )
    ),
    ids=lambda tup: f"Look for {tup[1]} in {tup[0]}",
)
def test_get_attribute_by_path(path):
    *_, location = path[0].split(".")
    attribute_name = path[1]
    if attribute_name == "foz" or location == "nonexistent_child":
        attribute_value = None
    else:
        attribute_value = f"{location}_bar"

    attribute_name = f"{location}_" + attribute_name
    if location == "root":
        location = None

    if location:
        attribute_path = f"{'.'.join(_ + [location])}.{attribute_name}"
    else:
        attribute_path = f"{attribute_name}"

    assert (
        get_attribute_by_path(attribute_path=attribute_path, config=source_config)
        == attribute_value
    )


@pytest.mark.parametrize(
    "mode",
    product(
        [("create", "node"), ("create", "table"), ("update", "node")],
        ["root", "parent", "child"],
    ),
    ids=lambda tup: f"{tup[0][0]} {tup[0][1]} in {tup[1]} table",
)
def test_create_or_update_attribute(mode):
    (action, obj), where = mode
    value = "baz"
    if action == "update":
        attribute_path = f"{where}_foo"
    else:
        attribute_path = "foz"

    if obj == "table":
        attribute_path = "new_table." + attribute_path

    if where == "parent":
        attribute_path = "parent." + attribute_path
    elif where == "child":
        attribute_path = "parent.child." + attribute_path

    updated_config = create_update_attr(
        attribute=attribute_path, value=value, config=source_config
    )
    assert (
        updated_config != source_config
    ), "This function should not change the original content"
    assert (
        get_attribute_by_path(attribute_path=attribute_path, config=updated_config)
        == value
    )
    assert updated_config["control_value"] == "value"
    # Test that the attribute is actually added and found
    # Maybe move this to a separate test? Probably dup?
    if action == "update":
        checked_attributes = get_filled_attributes(source_config)
    else:
        checked_attributes = get_filled_attributes(source_config) + (attribute_path,)

    assert set(checked_attributes) == set(get_filled_attributes(updated_config))


def test_get_filled_attributes():
    assert get_filled_attributes(source_config) == (
        "root_foo",
        "control_value",
        "parent.parent_foo",
        "parent.child.child_foo",
    )


def test_get_filled_attributes_empty():
    assert get_filled_attributes(parse("")) == ()


def test_get_filled_attributes_from_file_param_conversion(create_config_file):
    config = create_config_file
    assert get_filled_attributes_from_file(config) == get_filled_attributes_from_file(
        str(config)
    )
    assert get_filled_attributes_from_file(config) == {
        "root_foo",
        "control_value",
        "parent.parent_foo",
        "parent.child.child_foo",
    }


def test_get_filled_attributes_from_file_non_existent_file(tmp_path):
    """Ensures that empty file returns empty set of filled in params"""
    assert get_filled_attributes_from_file(tmp_path / "does not exist") == frozenset([])


@pytest.mark.parametrize(
    "parameter,default_value,_input,output",
    [
        ("name", None, "value", "value"),
        (DialogParameter("title", comment="Some comment"), None, "value", "value"),
        (
            DialogParameter(
                "is_cloud",
                type=bool,
                comment="Whether this is a cloud instance of Confluence.",
            ),
            None,
            "true",
            True,
        ),
        (
            DialogParameter("is_cloud", type=bool, comment="Some comment"),
            True,
            "",
            True,
        ),
        (DialogParameter("page_space", required=False), None, "", None),
        (DialogParameter("page_space", required=False), "LOC", "", "LOC"),
        (
            DialogParameter("password", hide_input=True),
            None,
            "my_password",
            "my_password",
        ),
        (DialogParameter("password", hide_input=True, required=False), None, "", None),
        (
            DialogParameter("password", hide_input=True, required=False),
            "pwd",
            "",
            "pwd",
        ),
    ],
    ids=[
        "Check str > output conversion",
        "Check DialogParameter[str] with comment",
        "Check DialogParameter[bool] with comment",
        "Check DialogParameter[bool] with comment and default True value",
        "Check optional DialogParameter[str]: skip the parameter",
        "Check optional DialogParameter[str]: accept the default value",
        "Check parameter with hidden input",
        "Check optional parameter with hidden input and empty default: skip",
        "Check optional parameter with hidden input and filled in default: accept default",
    ],
)
def test_single_dialog_prompt(
    monkeypatch, capsys, default_value, parameter, _input, output
):
    monkeypatch.setattr("sys.stdin", io.StringIO(_input + "\n"))
    # Otherwise the coverage test fails
    monkeypatch.setattr("getpass.getpass", lambda x: output)
    assert _dialog_prompt(parameter=parameter, default_value=default_value) == output
    captured = capsys.readouterr()

    if isinstance(parameter, DialogParameter):
        if parameter.comment is not None:
            assert (
                parameter.comment in captured.out
            ), "Comment should be displayed in dialog prompt"
        if parameter.hide_input and output is not None:
            assert output not in captured.out


def test_single_dialog_prompt_extra_line(monkeypatch, capsys):
    """Checks that dialogs are output in the format
    Title
    Comment: foo
    Value: <user input>
    """
    monkeypatch.setattr("sys.stdin", io.StringIO("value" + "\n"))
    _dialog_prompt(
        parameter=DialogParameter("Title", comment="Comment"),
    )
    captured = capsys.readouterr()
    assert captured.out.count("\n") == 2


def test_dialog_parameter_methods():
    inner_string = "title"
    d1 = DialogParameter(inner_string)
    d2 = DialogParameter(inner_string)
    d3 = DialogParameter(inner_string + "2")
    assert d1 == d2
    assert d1 != d3
    assert d1 == inner_string
    with pytest.raises(ValueError):
        assert DialogParameter("title") == 5

    assert d1 in [inner_string, d1, "Garbage"]
    assert d1 in (inner_string, d1, "Garbage")

    assert d1 in {"Garbage", inner_string}
    assert str(d1) == inner_string


@pytest.mark.parametrize("pages_amount", (0, 1, 2))
def test_generate_next_page(tmp_path, pages_amount):
    config = tmp_path / "config.toml"
    config.write_text("[pages]\n[pages.default]\npage_space = 'LOC'\n")
    with config.open("a") as f:
        for page_no in range(1, pages_amount + 1):
            f.write(f"[pages.page{page_no}]\npage_title = 'foz'\n")

    assert generate_next_page(config) == pages_amount + 1
