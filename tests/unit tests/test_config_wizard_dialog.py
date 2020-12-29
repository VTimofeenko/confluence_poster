import io
from confluence_poster.config_wizard import config_dialog
from pathlib import Path
from typer.testing import CliRunner
from tomlkit import parse
import pytest
from typing import List
from itertools import product
# noinspection PyProtectedMember
from confluence_poster.config_wizard import _get_attribute_by_path as get_attribute_by_path
from confluence_poster.config_wizard import print_config_file

pytestmark = pytest.mark.offline

runner = CliRunner()


def setup_input(monkeypatch, cli_input: List[str]):
    """Macro to monkeypatch th"""
    monkeypatch.setattr('sys.stdin', io.StringIO("\n".join(cli_input) + "\n"))


@pytest.mark.parametrize('save_agree', [True, False, None],
                         ids=['User explicitly agrees to save file',
                              'User hits enter to save file - the default choice',
                              'User refuses to save the file'])
def test_single_dialog_new_config(tmp_path, monkeypatch, save_agree):
    """Tests single run of config_dialog by populating a blank file"""
    path: Path = tmp_path / 'config.toml'
    # File will be created as a result of the test
    file_created = save_agree or save_agree is None

    if save_agree:
        save_agree = "Y"
    elif save_agree is None:
        save_agree = ''
    else:
        save_agree = 'N'

    # The monkey patched test cli_input. Should be the same length as the list of params fed to config_dialog later
    # Note: click provides validations for confirmation prompts, no need to test for garbage cli_input
    test_input = ["author name", 'https://confluence.local', 'page title', save_agree]
    setup_input(monkeypatch, test_input)

    # In this scenario file should be created when and only when the function returned true
    assert config_dialog(Path(path), ['author', 'auth.url', 'pages.page1.page_title']) == path.exists()
    if file_created:
        assert path.read_text() == """author = "author name"

[auth]
url = "https://confluence.local"

[pages]
[pages.page1]
page_title = "page title"
"""


def test_dialog_converts_filename_to_path(tmp_path, monkeypatch):
    """Makes sure the dialog accepts both Path and strings for config file"""
    path_as_path: Path = tmp_path / 'config_path.toml'
    path_as_string: str = str(tmp_path / 'config_string.toml')

    # In this scenario file should be created when and only when the function returned true
    for tested_type in [path_as_path, path_as_string]:
        # Taken from previous test
        test_input = ["author name", 'https://confluence.local', 'page title', "Y"]
        setup_input(monkeypatch, test_input)
        assert config_dialog(tested_type, ['author', 'auth.url', 'pages.page1.page_title'])
        assert Path(tested_type).exists()


@pytest.fixture(scope='function')
def prepare_config_file(tmp_path) -> (Path, str):
    config: Path = tmp_path / 'config.toml'
    config_text = """update_node = 'original_value'

    [parent]
    parent_update_node = 'parent_original_value'"""
    config.write_text(config_text)
    return config, config_text


# The underlying function is fully tested in unit tests, just need to test the UI wrapper around it
@pytest.mark.parametrize('user_agrees_to_overwrite_file,mode',
                         [(True, 'insert'),
                          (False, None)],
                         ids=["User adds a key to existing config",
                              "User decides not to overwrite the file"])
def test_single_dialog_existing_file_base(mode, user_agrees_to_overwrite_file,
                                          prepare_config_file,
                                          monkeypatch):
    config, config_text = prepare_config_file
    new_value = 'new_value'

    if user_agrees_to_overwrite_file:
        user_input = ['Y', new_value, 'Y']
    else:
        user_input = ['N']

    setup_input(monkeypatch, user_input)

    if user_agrees_to_overwrite_file:
        node_path = 'new_node'
        assert config_dialog(config, [node_path])
        assert parse(config.read_text())[node_path] == new_value, "Value was not set to the new one"
    else:
        assert config_dialog(config, ['update']) is None
        assert config.read_text() == config_text


@pytest.mark.parametrize('user_input', ['Y', 'N', ''],
                         ids=["User agrees to update parameter",
                              "User refuses to update parameter",
                              "User accepts the default choice to update parameter"])
def test_single_dialog_existing_file_one_update(user_input, prepare_config_file, monkeypatch):
    """This test checks that key update in the config works:
    * User input:
        * 'n' -> no update
        * 'y' -> update
        * '' -> update
    * If update happens - key is really updated
    """
    config, config_text = prepare_config_file
    new_value = "new_value"
    test_input = ['Y',  # overwrite file
                  user_input,  # whether the value should be updated
                  new_value,  # new value for the parameter
                  "Y"  # save the file
                  ]
    setup_input(monkeypatch, test_input)

    assert config_dialog(config, ['update_node'])
    if user_input in ['Y', '']:
        assert parse(config.read_text())['update_node'] == new_value, "Existing value was not updated"
    else:
        assert config.read_text() == config_text


@pytest.mark.parametrize('user_updates_values', product([True, False], repeat=2),
                         ids=lambda tup: f'User does {tup[0] * "not"} update the first attribute, '
                                         f'does {tup[1] * "not"} update the second attribute')
def test_single_dialog_existing_file_multiple_updates(user_updates_values, prepare_config_file, monkeypatch):
    """In a scenario where there are more than 1 keys to update - make sure that permutations of user input are
    handled correctly"""
    new_value = 'new_value'
    update_attrs = ['update_node', 'parent.parent_update_node']
    answer_1, answer_2 = user_updates_values
    config, config_text = prepare_config_file
    test_input = ["Y"]
    for user_answer in [answer_1, answer_2]:
        if user_answer:
            test_input += ['Y', new_value]
        else:
            test_input += ['N']
    test_input += ['Y']
    setup_input(monkeypatch, test_input)

    assert config_dialog(config, update_attrs)
    for user_answer, attr in zip([answer_1, answer_2], update_attrs):
        # The value should be updated <=> user said yes
        assert user_answer == (get_attribute_by_path(attribute_path=attr,
                                                     config=parse(config.read_text())) == new_value)


def test_config_file_printing(prepare_config_file):
    config, config_text = prepare_config_file
    tested_path = "parent.parent_update_node"

    assert print_config_file(config, []) == print_config_file(str(config), [])
    original_value = get_attribute_by_path(tested_path, parse(config_text))
    assert original_value not in print_config_file(config, [tested_path])
