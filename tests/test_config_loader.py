from confluence_poster.poster_config import Config
import toml
from confluence_poster.config_loader import load_config, merge_configs
from utils import mk_tmp_file
from pathlib import Path
import pytest

pytestmark = pytest.mark.offline


@pytest.fixture(scope='function')
def setup_xdg_dirs(tmp_path):
    my_xdg_config_dirs = [tmp_path / 'config_dirs_1', tmp_path / 'config_dirs_2']  # TODO: multiple
    my_xdg_config_home = tmp_path / 'config_home'
    [_.mkdir() for _ in my_xdg_config_dirs]
    my_xdg_config_home.mkdir()
    for path in my_xdg_config_dirs + [my_xdg_config_home]:
        _ = path / 'confluence_poster'
        _.mkdir()
    return ':'.join([str(_) for _ in my_xdg_config_dirs]), str(my_xdg_config_home)


@pytest.mark.parametrize('dir_undefined', [None, 'home', 'dirs'])
def test_config_construct(tmp_path, setup_xdg_dirs, monkeypatch, dir_undefined):
    """Creates all XDG_CONFIG_ dirs for the test and checks that relevant keys are constructed"""
    my_xdg_config_dirs, my_xdg_config_home = setup_xdg_dirs
    global_config = Path(f"{my_xdg_config_dirs.split(':')[0]}/confluence_poster/config.toml")
    home_config = Path(f"{my_xdg_config_home}/confluence_poster/config.toml")
    repo_config = toml.load('config.toml')

    # Strip repo config into parts
    if dir_undefined == 'home':
        global_config_part = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()}
        my_xdg_config_home = None
    else:
        global_config_part = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()
                              & {'confluence_url', 'is_cloud'}}
    global_config.write_text(toml.dumps({'auth': global_config_part}))

    if dir_undefined == 'dirs':
        home_config_part = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()}
        my_xdg_config_dirs = None
    else:
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
    assert dict(merge_configs({'auth': {'password': 'a'}}, {'auth': {'password': 'b'}})) == \
           {'auth': {'password': 'b'}}

    with pytest.raises(ValueError):
        dict(merge_configs({'a': {'b': 'c'}}, {'a': 'd'}))
    with pytest.raises(ValueError):
        dict(merge_configs({'a': {'b': 'c'}}, {'a': {'b': 1}}))


def test_no_configs_except_local(monkeypatch):
    """Checks that the script works if only the local config exists"""
    monkeypatch.setenv('XDG_CONFIG_HOME', None)
    monkeypatch.setenv('XDG_CONFIG_DIRS', None)
    _ = load_config(Path('config.toml'))
    repo_config = Config('config.toml')
    assert repo_config == _


def test_multiple_xdg_config_dirs(tmp_path, setup_xdg_dirs, monkeypatch):
    """Checks that the value from leftmost XGD_CONFIG_DIRS is the applied one"""
    my_xdg_config_dirs, _ = setup_xdg_dirs
    monkeypatch.setenv('XDG_CONFIG_DIRS', my_xdg_config_dirs)
    my_xdg_config_dirs = my_xdg_config_dirs.split(':')

    repo_config = toml.load('config.toml')
    global_config = {key: repo_config['auth'][key] for key in repo_config['auth'].keys()}
    global_config_file_1 = Path(f"{my_xdg_config_dirs[0]}/confluence_poster/config.toml")
    global_config_file_2 = Path(f"{my_xdg_config_dirs[1]}/confluence_poster/config.toml")

    global_config.update({'username': 'user1'})
    global_config_file_1.write_text(toml.dumps({'auth': global_config}))
    global_config.update({'username': 'user2'})
    global_config_file_2.write_text(toml.dumps({'auth': global_config}))

    config_file = mk_tmp_file(tmp_path=tmp_path, key_to_pop='auth')
    _ = load_config(local_config=config_file)

    config_file = mk_tmp_file(tmp_path=tmp_path, key_to_update='auth.username', value_to_update='user1')
    assert Config(config_file) == _
