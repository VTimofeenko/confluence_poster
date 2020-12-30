from jinja2 import Environment, FileSystemLoader
from subprocess import run
from pathlib import Path
import sys
from typing import Dict, List
import re

TOOL_NAME = "confluence_poster"


def get_typer_cli_docs() -> str:
    """Extracts the stdout from typer docs generator"""
    typer_docs = run(f"{sys.executable} -m typer_cli "  # to make sure venv is used
                     f"confluence_poster/main.py utils docs --name {TOOL_NAME}".split(" "),
                     capture_output=True,
                     text=True)
    assert typer_docs.returncode == 0
    return str(typer_docs.stdout)


def process_chapters(chapters: List[str]) -> Dict[str, Dict[str, str]]:
    """Reprocesses chapters. Contains logic on changing the data inside the chapters"""
    result = {}
    _chapters = chapters.copy()
    for chapter in _chapters:
        if chapter.startswith("#"):  # h1
            chapter_title = "Description"
            chapter = chapter.replace(f"`{TOOL_NAME}`", chapter_title, 1)
        else:
            chapter_title = re.findall('`[a-zA-Z-_ ]*`', chapter)[0]
            chapter = "##" + chapter

        intro, *_ = chapter.partition("**Usage**")  # "Usage" always exists
        result.update({chapter_title: {"intro": intro.rstrip()}})
        the_rest = "".join(_)
        sections = list(enumerate(["usage", "arguments", "options", "commands"]))
        for number, section in sections:
            index = the_rest.find(f"**{section.capitalize()}**")
            if index == -1:
                continue
            else:
                next_index = -1
                for _, next_section in sections[number+1:]:
                    next_index = the_rest.find(f"**{next_section.capitalize()}**")
                    if next_index != -1:
                        break
                if next_index == -1:  # next section not found
                    value = the_rest
                else:
                    value, the_rest = the_rest[:next_index], the_rest[next_index:]
            result[chapter_title].update({section: value.rstrip()})

    return result


def render_template() -> str:
    env = Environment(loader=FileSystemLoader(str(Path.cwd()) + '/docs/templates'), autoescape=False)
    env.lstrip_blocks = True
    env.trim_blocks = True

    template = env.get_template('skeleton.jinja2')
    typer_cli_help: str = get_typer_cli_docs()
    chapters = process_chapters(typer_cli_help.split("##"))

    sample_config = Path('config.toml').read_text()
    return template.render(typer_help_chapters=chapters, tool_name=TOOL_NAME, config_toml=sample_config)


def generate_docs():
    print(render_template())

if __name__ == "__main__":
    Path("README.md").write_text(render_template())
