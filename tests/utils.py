import toml
import pytest
from os import environ
from typer.testing import CliRunner
from functools import partial
from typing import Callable, Union, List
from faker import Faker


real_confluence_config = 'local_config.toml'  # The config filename for testing against local instance


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


def clone_local_config(other_config: str = real_confluence_config,
                       ):
    """Shorthand to copy the config to be used against local instance of confluence"""
    return partial(mk_tmp_file, config_to_clone=other_config)


def mark_online_only():
    """Marks the test 'online-only' - i.e. tests will be run only if the proper environment variable is iset"""
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
    """Generates a .confluencewiki file filled with random stuff. Also generates a cloned real confluence config
    with one page path updated"""
    if filename is None:
        fake_file = tmp_path / f"{tmp_path.name}.confluencewiki"
    else:
        fake_file = tmp_path / f"{filename}.confluencewiki"
    fake_text = Faker().paragraph(nb_sentences=10)
    fake_file.write_text(fake_text)

    fake_config = mk_tmp_file(tmp_path, filename="fakeconfig.toml",
                              config_to_clone=real_confluence_config,
                              key_to_update="pages.page1.page_file", value_to_update=str(fake_file))

    return fake_file, fake_text, fake_config


def gen_fake_title():
    """Generates a fake page title. Default fixture behavior is to purge .unique which does not work for my tests"""
    f = Faker()
    while True:
        yield f.sentence(nb_words=3)


fake_title_generator = gen_fake_title()

def generate_fake_content():
    f = Faker()
    while True:
        yield f.paragraph(nb_sentences=10)


fake_content_generator = generate_fake_content()


def generate_fake_page(tmp_path) -> (str, str, str):
    """Generates a title, fake content and the path to the temporary file in temporary path"""
    title = next(fake_title_generator)
    content = next(fake_content_generator)
    filename = tmp_path / title.lower().replace(' ', '_')
    filename.write_text(content)
    return title, content, str(filename)


def generate_local_config(tmp_path, pages: int = 1) -> str:
    """Clones the auth and default space from local config, and generates the required amount of pages"""
    new_config = clone_local_config()(tmp_path, key_to_pop = "pages.page1")
    for page_number in range(pages):
        pass