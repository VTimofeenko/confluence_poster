from confluence_poster.poster_config import Config, PartialConfig
import toml
from confluence_poster.config_loader import load_config, merge_configs
from utils import mk_tmp_file
from pathlib import Path
import pytest

pytestmark = pytest.mark.offline


@pytest.fixture(scope='function')
def setup_xdg_dirs(tmp_path):
    my_xdg_config_dirs = tmp_path / 'config_dirs'  # TODO: multiple
    my_xdg_config_home = tmp_path / 'config_home'
    my_xdg_config_dirs.mkdir()
    my_xdg_config_home.mkdir()
    for path in [my_xdg_config_dirs, my_xdg_config_home]:
        _ = path / 'confluence_poster'
        _.mkdir()
    return str(my_xdg_config_dirs), str(my_xdg_config_home)


def test_config_construct(tmp_path, setup_xdg_dirs, monkeypatch):
    """Creates all XDG_CONFIG_ dirs for the test and checks that relevant keys are constructed, without override"""
    my_xdg_config_dirs, my_xdg_config_home = setup_xdg_dirs
    global_config = Path(f"{my_xdg_config_dirs}/confluence_poster/config.toml")
    home_config = Path(f"{my_xdg_config_home}/confluence_poster/config.toml")
    repo_config = toml.load('config.toml')

    # Strip repo config into parts
    global_config_part = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()
                          & {'confluence_url', 'is_cloud'}}
    global_config.write_text(toml.dumps({'auth': global_config_part}))

    home_config_part = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()
                        & {'username', 'password'}}
    home_config.write_text(toml.dumps({'auth': home_config_part}))

    # Set up dirs and files for test
    config_file = mk_tmp_file(tmp_path=tmp_path, key_to_pop='auth')
    monkeypatch.setenv('XDG_CONFIG_HOME', my_xdg_config_home)
    monkeypatch.setenv('XDG_CONFIG_DIRS', my_xdg_config_dirs)

    _ = load_config(local_config=config_file)
    repo_config = Config('config.toml')
    assert repo_config == _


def test_util_merge():
    """Tests the utility function that merges configs"""
    assert dict(merge_configs({'a': 'b'}, {'c': 'd'})) == {'a': 'b', 'c': 'd'}
    assert dict(merge_configs({'auth': {'user': 'a'}}, {'auth': {'password': 'b'}})) == \
           {'auth': {'user': 'a', 'password': 'b'}}
    with pytest.raises(ValueError):
        dict(merge_configs({'a': {'b': 'c'}}, {'a': 'd'}))


def test_config_no_xdg_config_home(tmp_path):
    """Checks that configs work if xdg_home is not overridden"""


def test_config_no_xdg_config_dirs(tmp_path):
    pass


def test_no_configs_except_local(tmp_path):
    """Checks that the script works if only the local config exists"""
