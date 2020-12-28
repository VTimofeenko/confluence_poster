from tomlkit import dumps, parse
from pathlib import Path
# noinspection PyProtectedMember
from confluence_poster.config_wizard import _create_or_update_attribute as create_update_attr
# noinspection PyProtectedMember
from confluence_poster.config_wizard import _get_attribute_by_path as get_attribute_by_path
# noinspection PyProtectedMember
from confluence_poster.config_wizard import _get_filled_attributes as get_filled_attributes
from confluence_poster.config_wizard import get_filled_attributes_from_file
import pytest
from itertools import product

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


@pytest.mark.parametrize('path',
                         product(['root', 'parent', 'parent.child', 'parent.child.nonexistent_child'],
                                 ['foo', 'foz']),
                         ids=lambda tup: f'Look for {tup[1]} in {tup[0]}')
def test_get_attribute_by_path(path):
    *_, location = path[0].split('.')
    attribute_name = path[1]
    if attribute_name == 'foz' or location == 'nonexistent_child':
        attribute_value = None
    else:
        attribute_value = f"{location}_bar"

    attribute_name = f"{location}_" + attribute_name
    if location == 'root':
        location = None

    if location:
        attribute_path = f"{'.'.join(_ + [location])}.{attribute_name}"
    else:
        attribute_path = f"{attribute_name}"

    assert get_attribute_by_path(attribute_path=attribute_path,
                                 config=source_config) == attribute_value


@pytest.mark.parametrize('mode', product([
    ('create', 'node'), ('create', 'table'), ('update', 'node')],
    ['root', 'parent', 'child']),
    ids=lambda tup: f'{tup[0][0]} {tup[0][1]} in {tup[1]} table'
)
def test_create_or_update_attribute(mode):
    (action, obj), where = mode
    value = 'baz'
    if action == 'update':
        attribute_path = f'{where}_foo'
    else:
        attribute_path = 'foz'

    if obj == 'table':
        attribute_path = 'new_table.' + attribute_path

    if where == 'parent':
        attribute_path = 'parent.' + attribute_path
    elif where == 'child':
        attribute_path = 'parent.child.' + attribute_path

    updated_config = create_update_attr(attribute=attribute_path,
                                        value=value,
                                        config=source_config)
    assert updated_config != source_config, "This function should not change the original content"
    assert get_attribute_by_path(attribute_path=attribute_path, config=updated_config) == value
    assert updated_config['control_value'] == 'value'
    # Test that the attribute is actually added and found
    # Maybe move this to a separate test? Probably dup?
    if action == 'update':
        checked_attributes = get_filled_attributes(source_config)
    else:
        checked_attributes = get_filled_attributes(source_config) + (attribute_path,)

    assert set(checked_attributes) == set(get_filled_attributes(updated_config))


def test_get_filled_attributes():
    assert get_filled_attributes(source_config) == ('root_foo', 'control_value',
                                                    'parent.parent_foo',
                                                    'parent.child.child_foo')


def test_get_filled_attributes_empty():
    assert get_filled_attributes(parse("")) == ()


def test_get_filled_attributes_from_file_param_conversion(create_config_file):
    config = create_config_file
    assert get_filled_attributes_from_file(config) == get_filled_attributes_from_file(str(config))
    assert get_filled_attributes_from_file(config) == {'root_foo', 'control_value',
                                                       'parent.parent_foo',
                                                       'parent.child.child_foo'}


def test_get_filled_attributes_from_file_non_existent_file(tmp_path):
    """Ensures that empty file returns empty set of filled in params"""
    assert get_filled_attributes_from_file(tmp_path / "does not exist") == frozenset([])
