import toml
from typer.testing import CliRunner, Result
from functools import partial
from typing import Callable, Union, List, Set, Iterable
from faker import Faker
from confluence_poster.poster_config import Config, Page
from atlassian import Confluence
from pathlib import Path
import re
from inspect import currentframe


real_confluence_config = (
    "local_config.toml"  # The config filename for testing against local instance
)
other_user_config = "local_config_other_user.toml"  # Config with a different user
created_pages = set()

if Path(real_confluence_config).exists():
    real_config = Config(real_confluence_config)
    confluence_instance = Confluence(
        url=real_config.auth.url,
        username=real_config.auth.username,
        password=real_config.auth.password,
    )
else:
    print(
        f"Config for testing local confluence: {real_confluence_config} does not exist."
    )
    confluence_instance = None


def mk_tmp_file(
    tmp_path,
    filename: str = None,
    config_to_clone: str = "config.toml",
    key_to_pop: str = None,  # key path in form 'first_key.second_key' to descend into config
    key_to_update: str = None,
    value_to_update=None,
):
    # Helper function to break config file in various ways
    if [key_to_update, value_to_update].count(
        None
    ) == 1:  # TODO: 'not supplied' vs 'supplied None'
        raise ValueError("Only one update-related parameter was supplied")

    if filename is None:
        config_file = tmp_path / tmp_path.name
    else:
        config_file = tmp_path / filename
    original_config = toml.load(config_to_clone)
    if key_to_pop:
        _ = original_config
        li = key_to_pop.split(".")
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.pop(key)
    if key_to_update:
        _ = original_config
        li = key_to_update.split(".")
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.update({key: value_to_update})
    config_file.write_text(toml.dumps(original_config))
    return config_file


def clone_local_config(other_config: str = real_confluence_config):
    """Shorthand to copy the config to be used against local instance of confluence"""
    return partial(mk_tmp_file, config_to_clone=other_config)


def generate_run_cmd(
    runner: CliRunner, app, default_args: Union[List, None] = None
) -> Callable:
    """Config may be either string with path to config file or path object itself"""
    if default_args is None:
        default_args = []

    def _run_with_config(
        config=real_confluence_config,
        pre_args: Union[List, None] = None,
        other_args: Union[List, None] = None,
        **kwargs,
    ):
        if pre_args is None:
            pre_args = []
        if not isinstance(config, str):
            config = str(config)
        if other_args is None:
            other_args = []
        return runner.invoke(
            app, ["--config", config] + pre_args + default_args + other_args, **kwargs
        )

    return _run_with_config


def mk_fake_file(tmp_path, filename: str = None):
    """Generates a .confluencewiki file filled with random stuff. Also generates a cloned real confluence config
    with one page path updated"""
    if filename is None:
        fake_file = tmp_path / f"{tmp_path.name}.confluencewiki"
    else:
        fake_file = tmp_path / f"{filename}.confluencewiki"
    fake_text = Faker().paragraph(nb_sentences=10)
    fake_file.write_text(fake_text)

    fake_config = mk_tmp_file(
        tmp_path,
        filename="fake_config.toml",
        config_to_clone=real_confluence_config,
        key_to_update="pages.page1.page_file",
        value_to_update=str(fake_file),
    )

    return fake_file, fake_text, fake_config


def gen_fake_title():
    """Generates a fake page title. Default fixture behavior is to purge .unique which does not work for my tests"""
    f = Faker()
    while True:
        yield "pytest: " + f.sentence(nb_words=3)


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
    filename = tmp_path / f'{title.lower().replace(" ", "_")}.confluencewiki'
    filename.write_text(content)
    return title, content, str(filename)


def generate_local_config(
    tmp_path, pages: int = 1, filename: str = None
) -> (str, Config):
    """Clones the auth and default space from local config, and generates the required amount of pages.
    Returns path to the new config and instance of it"""
    if filename is None:
        filename = "local_config.toml"

    new_config = clone_local_config()(
        tmp_path, filename=filename, key_to_pop="pages.page1"
    )
    for page_number in range(pages):
        title, _, filename = generate_fake_page(tmp_path)
        new_config = mk_tmp_file(
            tmp_path,
            filename=str(new_config),
            config_to_clone=new_config,
            key_to_update=f"pages.page{page_number+1}",
            value_to_update={"page_title": title, "page_file": filename},
        )
    return new_config, Config(str(new_config))


def page_created(page_title: str, space: str = None) -> bool:
    """Checks that the page has been created by looking it up by title"""
    if space is None:
        space = real_config.pages[0].page_space
    return (
        confluence_instance.get_page_by_title(space=space, title=page_title) is not None
    )


def get_pages_ids_from_stdout(stdout: str) -> Union[Set[int], Set]:
    """Returns list of pages from stdout"""
    if result := re.findall("Created page #[0-9]+", stdout):
        return set([_.split("#")[1] for _ in result])
    else:
        return set()


def get_page_id_from_stdout(stdout: str) -> Union[int, None]:
    """Function to parse stdout and get the created page id"""
    if len(result := get_pages_ids_from_stdout(stdout)) == 1:
        return result.pop()
    elif len(result) == 0:
        return None
    else:
        raise ValueError("Returned multiple page ids!")


def check_body_and_title(page_id: int, body_text: str, title_text: str):
    assert body_text in get_page_body(page_id)
    assert title_text in get_page_title(page_id)


def get_page_body(page_id):
    return (
        confluence_instance.get_page_by_id(page_id, expand="body.storage")
        .get("body")
        .get("storage")
        .get("value")
    )


def get_page_title(page_id):
    return confluence_instance.get_page_by_id(page_id, expand="body.storage").get(
        "title"
    )


def run_with_config(
    config_file, default_run_cmd: Callable, record_pages: set = None, *args, **kwargs
) -> Result:
    """Function that runs the default_run_cmd with supplied config and records the generated pages in the fixture"""
    result = default_run_cmd(config=config_file, *args, **kwargs)
    # This allows manipulating the set of the pages to be destroyed at the end
    _created_pages = get_pages_ids_from_stdout(result.stdout)
    if _created_pages:
        frame = currentframe()
        while True:
            # go back the stack
            frame = frame.f_back
            if frame is None:
                _record_pages = (
                    record_pages  # for cases when this is called from fixture
                )
                break
            if (
                _record_pages := frame.f_locals.get("funcargs", {}).get("record_pages")
            ) is not None:
                # if global fixture is found
                break

        assert (
            type(_record_pages) is set
        ), "Looks like record_set manipulation is going to fail"
        _record_pages |= _created_pages
    config = Config(config_file)
    for page_id in _created_pages:
        """Make sure that the pages got created with proper content"""
        if "pre_args" in kwargs and "--page-title" in kwargs.get("pre_args"):
            # Page title specified manually, only one page in config
            found_page = config.pages[0]
            _ = kwargs.get("pre_args").index("--page-title")
            page_title = kwargs.get("pre_args")[_ + 1]
        else:
            page_title = get_page_title(page_id)
            found_page: Page = next(
                _ for _ in config.pages if _.page_title == page_title
            )

        with open(found_page.page_file, "r") as page_file:
            page_text = page_file.read()
            assert page_text in get_page_body(
                page_id
            ), f"Page {page_title} has incorrect content"

    return result


def join_input(_input: Iterable) -> str:
    return "\n".join(_input) + "\n"
