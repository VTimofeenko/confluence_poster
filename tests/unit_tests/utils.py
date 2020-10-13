import toml
import pytest
from os import environ
from typer.testing import CliRunner
from functools import partial
from typing import Callable, Union, List
from faker import Faker


def mk_tmp_file(tmp_path, filename: str = None,
                config_to_clone: str = 'config.toml',
                key_to_pop: str = None,  # key path in form 'first_key.second_key' to descend into config
                key_to_update: str = None, value_to_update=None):
    # Helper function to break config file in various ways
    if [key_to_update, value_to_update].count(None) == 1:  # TODO: 'not supplied' vs 'supplied None'
        raise ValueError("Only one update-related parameter was supplied")

    if filename is None:
        config_file = tmp_path / tmp_path.name
    else:
        config_file = tmp_path / filename
    original_config = toml.load(config_to_clone)
    if key_to_pop:
        _ = original_config
        li = key_to_pop.split('.')
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.pop(key)
    if key_to_update:
        _ = original_config
        li = key_to_update.split('.')
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.update({key: value_to_update})
    config_file.write_text(toml.dumps(original_config))
    return config_file


real_confluence_config = 'local_config.toml'  # The config filename for testing against local instance


def clone_local_config(other_config: str = real_confluence_config,
                       ):
    """Shorthand to copy the config to be used against local instance of confluence"""
    return partial(mk_tmp_file, config_to_clone=other_config)


def mark_online_only():
    return pytest.mark.skipif(environ.get("VALIDATE_ONLINE", None) != "yes",
                              reason="Environment variable is not set to test against an instance of Confluence")


def generate_run_cmd(runner: CliRunner, app,
                     default_args: Union[List, None] = None) -> Callable:
    """Config may be either string with path to config file or path object itself"""
    if default_args is None:
        default_args = []

    def run_with_config(config=real_confluence_config,
                        pre_args: Union[List, None] = None,
                        other_args: Union[List, None] = None,
                        **kwargs):
        if pre_args is None:
            pre_args = []
        if not isinstance(config, str):
            config = str(config)
        if other_args is None:
            other_args = []
        return runner.invoke(app, ["--config", config] + pre_args + default_args + other_args, **kwargs)
    return run_with_config


def mk_fake_file(tmp_path,
                 filename: str = None):
    if filename is None:
        fake_file = tmp_path / tmp_path.name
    else:
        fake_file = tmp_path / filename
    fake_text = Faker().paragraph(nb_sentences=10)
    fake_file.write_text(fake_text)
    return fake_file, fake_text
