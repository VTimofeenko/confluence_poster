from typer.testing import CliRunner, Result
from confluence_poster.main import app, default_config_name
from utils import generate_run_cmd
from pathlib import Path
import pytest


pytestmark = pytest.mark.offline

runner = CliRunner()
default_run_cmd = generate_run_cmd(runner=runner, app=app, default_args=['create-config'])


@pytest.fixture(autouse=True)
def setup_env_dirs(tmp_path, monkeypatch):
    new_home = tmp_path / 'home'
    cwd = tmp_path / 'cwd'
    (new_home / 'confluence_poster').mkdir(parents=True)
    cwd.mkdir()

    monkeypatch.setenv("XDG_CONFIG_HOME", str(new_home))
    monkeypatch.chdir(cwd)


@pytest.mark.parametrize('user_input', [('Y', 'Y', default_config_name),
                                        ('Y', 'N'),
                                        ('N', 'Y', default_config_name),
                                        ('N', 'N'),
                                        ('Q',),
                                        ('', '', default_config_name)],
                         ids=['User creates config in the home and in the local directory',
                              'User creates config in the home, but not in the local directory',
                              'User creates config only in the local directory',
                              'User creates config only in the local directory, quits',
                              'User quits the wizard',
                              'User accepts the default choices: create config in home, create local config'])
def test_no_params_dialog(user_input, tmp_path, monkeypatch):
    # noinspection PyUnusedLocal
    def mock_config_dialog(filename, *args, **kwargs):
        """Mocks the config dialog run by just creating the file and returning True"""
        Path(filename).touch()
        return True

    import confluence_poster.config_wizard as _config_wizard
    monkeypatch.setattr(_config_wizard, 'config_dialog', mock_config_dialog)

    # Since "user creates config in local directory" requires more user input (tested in a different place)
    result: Result = default_run_cmd(input="\n".join(user_input) + "\n")
    assert result.exit_code == 0

    # Home config exists <=> user replied "Y" on first question or accepted default
    assert ((tmp_path / 'home/confluence_poster/config.toml').exists()) == (user_input[0] in {'Y', ''})
    # Local config exists <=> user replied "Y" on first question or accepted default
    assert ((tmp_path / f'cwd/{default_config_name}').exists()) == (len(user_input) > 1 and user_input[1] in {'Y', ''})
