from confluence_poster.poster_config import Config, Page
from dataclasses import fields
import toml
import pytest


def mk_tmp_file(tmp_path, filename: str = None,
                config_to_clone: str = 'config.toml',
                key_to_pop: str = None,  # key path in form 'first_key.second_key' to descend into config
                key_to_update: str = None, value_to_update=None):
    # Helper function to break config file in various ways
    if [key_to_update, value_to_update].count(None) == 1:
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


def test_repo_sample_config():
    """General wellness test. The default config from repo should always work."""
    _ = Config("config.toml")
    # Just some random checks
    assert _.auth["is_cloud"] is False
    assert _.pages[0].page_name == "Some page name"
    assert len(_.pages) == 1


def test_no_auth(tmp_path):
    """Checks for error if there is no auth section at all"""
    config_file = mk_tmp_file(tmp_path=tmp_path, key_to_pop='auth')
    with pytest.raises(KeyError):
        _ = Config(config_file)


def test_bad_auth_mandatory_params(tmp_path):
    """Checks for proper error if one of the mandatory parameters is missing in auth """
    for param in ["confluence_url", "username", "is_cloud"]:
        config_file = mk_tmp_file(tmp_path, filename=param, key_to_pop=f"auth.{param}")
        with pytest.raises(KeyError) as e:
            _ = Config(config_file)
        assert e.value.args[0] == f"{param} not in auth section"


def test_auth_no_password_ok(tmp_path):
    """Passwords may come from environment or option to the main file. This test ensures that there is no exception
    in this case"""
    config_file = mk_tmp_file(tmp_path, key_to_pop=f"auth.password")
    _ = Config(config_file)
    assert _.auth['password'] is None


def test_no_author(tmp_path):
    """Checks that no author string will raise a key error"""
    config_file = mk_tmp_file(tmp_path, key_to_pop=f"author")

    with pytest.raises(KeyError):
        _ = Config(config_file)


def test_author_not_str(tmp_path):
    """Checks that exception is thrown if author is not a string"""
    config_file = mk_tmp_file(tmp_path, key_to_update="author", value_to_update=1)

    with pytest.raises(ValueError) as e:
        _ = Config(config_file)


def test_default_space(tmp_path):
    """Tests that space definition is applied from default section and
     it does not override specific definition from page """
    config_file = mk_tmp_file(tmp_path, key_to_pop="pages.page1.page_space",
                              key_to_update="pages.page2", value_to_update={'page_name': 'Page2',
                                                                            'page_path': '',
                                                                            'page_space': 'some_space'})
    _ = Config(config_file)
    # check if the default value was applied for page without full definition
    assert _.pages[0].page_space == "default space"
    # make sure the fully defined page definition is not overwritten
    assert _.pages[1].page_space == "some_space"


def test_no_default_space(tmp_path):
    """Tests that if there is no space definition in the default node, and there is no space in page definition,
    there will be an exception"""
    clean_config = toml.load("config.toml")
    config_file = tmp_path / str("no_default_space")
    clean_config['pages']['page1'].pop('page_space')
    clean_config['pages'].pop('default')
    config_file.write_text(toml.dumps(clean_config))

    with pytest.raises(ValueError) as e:
        _ = Config(config_file)
    assert "neither is default space" in e.value.args[0]


def test_broken_default_definition(tmp_path):
    """Checks integrity checks of default section"""
    config_file = mk_tmp_file(tmp_path, filename="default_no_value", key_to_update="pages.default", value_to_update='')
    with pytest.raises(ValueError) as e:
        _ = Config(config_file)
    assert "not a section" in e.value.args[0]


def test_default_page_space_not_str(tmp_path):
    config_file = mk_tmp_file(tmp_path,
                              key_to_update="pages.default.page_space", value_to_update=1)
    with pytest.raises(ValueError) as e:
        _ = Config(config_file)
    assert "should be a string" in e.value.args[0]


def test_page_section_not_dict(tmp_path):
    config_file = mk_tmp_file(tmp_path, key_to_update='pages.page1', value_to_update=1)
    with pytest.raises(ValueError) as e:
        _ = Config(config_file)
    assert "Pages section is malformed" in e.value.args[0]


def test_page_definition_not_str(tmp_path):
    """Defines each field one by one as a non-str and tests that exception is thrown"""
    for page_def in [_.name for _ in fields(Page)]:
        config_file = mk_tmp_file(tmp_path, key_to_update=f"pages.page1.{page_def}", value_to_update=1)
        with pytest.raises(ValueError) as e:
            _ = Config(config_file)
        assert f"{page_def} property of a page is not a string" in e.value.args[0]


def test_page_no_name_or_path(tmp_path):
    """Checks that lack of mandatory string definition is handled with an exception"""
    for page_def in [_.name for _ in fields(Page) if _.name != 'page_space']:
        config_file = mk_tmp_file(tmp_path, key_to_pop=f"pages.page1.{page_def}")
        with pytest.raises(KeyError) as e:
            _ = Config(config_file)
