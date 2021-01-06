from typer.testing import CliRunner, Result
from confluence_poster.main import app, default_config_name
from utils import generate_run_cmd
from pathlib import Path
import pytest


pytestmark = pytest.mark.offline

runner = CliRunner()
default_run_cmd = generate_run_cmd(
    runner=runner, app=app, default_args=["create-config"]
)


@pytest.fixture(autouse=True)
def setup_env_dirs(tmp_path, monkeypatch):
    new_home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    (new_home / "confluence_poster").mkdir(parents=True)
    cwd.mkdir()

    monkeypatch.setenv("XDG_CONFIG_HOME", str(new_home))
    monkeypatch.chdir(cwd)


# args and kwargs here suppress errors about extra arguments
# noinspection PyUnusedLocal
def mock_config_dialog(filename, *args, **kwargs):
    """Mocks the config dialog run by just creating the file and returning True"""
    Path(filename).touch()
    return True


def validate_config():
    result: Result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "user_input",
    [
        ("Y", "Y", default_config_name),
        ("Y", "N"),
        ("N", "Y", default_config_name),
        ("N", "N"),
        ("Q",),
        ("", "", default_config_name),
        ("", "", ""),
    ],
    ids=[
        "User creates config in the home and in the local directory",
        "User creates config in the home, but not in the local directory",
        "User creates config only in the local directory",
        "User creates config only in the local directory, quits",
        "User quits the wizard",
        "User accepts the default choices: create config in home, create local config",
        "User accepts default choice for local config name",
    ],
)
def test_no_params_initial_dialog(user_input: tuple, tmp_path, monkeypatch):
    """Tests the very first run of config wizard, assuming no files currently exist"""

    import confluence_poster.config_wizard as _config_wizard

    monkeypatch.setattr(_config_wizard, "config_dialog", mock_config_dialog)

    # Since "user creates config in local directory" requires more user input (tested in a different place)
    result: Result = default_run_cmd(
        input="\n".join(user_input + ("n",))  # extra 'n' to reject page_add_dialog
        + "\n"
    )
    assert result.exit_code == 0

    # Home config exists <=> user replied "Y" on first question or accepted default
    assert ((tmp_path / "home/confluence_poster/config.toml").exists()) == (
        user_input[0] in {"Y", ""}
    )
    # Local config exists <=> user replied "Y" on first question or accepted default
    assert ((tmp_path / f"cwd/{default_config_name}").exists()) == (
        len(user_input) > 1 and user_input[1] in {"Y", ""}
    )


def test_no_params_values_filled():
    """Goes through the wizard properly, checks that all values are filled"""
    _input = (
        "",
        "author",
        "http://confluence.local",
        "admin",
        "password",
        "false",
        "Y",  # save the edit
        "Y",  # create local config
        "",
        "LOC",  # default space
        "Some page title",
        "page1.confluencewiki",
        "confluencewiki",
        "LOC",
        "Y",  # save the edit
        "Y",  # add more pages
        "Other page title",
        "page2.confluencewiki",
        "",
        "LOC",
        "Y",
    )
    result: Result = default_run_cmd(input="\n".join(_input) + "\n")
    assert result.exit_code == 0
    validate_config()


@pytest.mark.parametrize(
    "flag", ["--home-only", "--local-only"], ids=lambda flag: f"Tests f{flag} flag"
)
def test_command_flags_no_configs(flag, tmp_path, monkeypatch):
    """Tests --home-only and --local-only dialogs create only the corresponding files"""
    import confluence_poster.config_wizard as _config_wizard

    monkeypatch.setattr(_config_wizard, "config_dialog", mock_config_dialog)

    if flag == "--home-only":
        _input = ()
    else:
        _input = (default_config_name, "N")

    result: Result = default_run_cmd(input="\n".join(_input) + "\n", other_args=[flag])
    assert result.exit_code == 0
    assert ((tmp_path / "home/confluence_poster/config.toml").exists()) == (
        flag == "--home-only"
    )
    assert ((tmp_path / f"cwd/{default_config_name}").exists()) == (
        flag == "--local-only"
    )


def test_prefilled_params(tmp_path):
    """Pre-fills the home config and checks that the user is asked relevant params for local config"""
    _home_config: Path = tmp_path / "home/confluence_poster/config.toml"
    home_config_text = "author = 'test user'"
    _home_config.write_text(home_config_text)
    _input = (
        "n",  # no, skip to local config
        "y",  # create local config
        "",  # accept default name for config
        "",
        "http://confluence.local",
        "admin",
        "password",
        "false",
        "LOC",  # default space
        "Some page title",
        "page1.confluencewiki",
        "LOC",  # page space
        "Y",  # save the edit
        "N",  # do not add any more pages
    )

    result: Result = default_run_cmd(input="\n".join(_input) + "\n")
    assert result.exit_code == 0
    validate_config()


def test_dialog_home_directory_created(tmp_path, monkeypatch):
    """Checks that XDG_CONFIG_HOME/confluence_poster directory is created if it does not exist"""
    new_home_config: Path = tmp_path / "new_home"  # new_home to override the fixture
    new_home_config.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(new_home_config))
    assert not (new_home_config / "confluence_poster").exists()
    _input = (
        "",
        "author",
        "http://confluence.local",
        "admin",
        "password",
        "false",
        "Y",  # save the edit
    )

    default_run_cmd(input="\n".join(_input) + "\n", other_args=["--home-only"])
    assert (new_home_config / "confluence_poster").exists()
