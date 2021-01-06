import pytest
from utils import setup_input

from confluence_poster.main_helpers import StateConfig


pytestmark = pytest.mark.offline


@pytest.mark.parametrize(
    "quiet",
    (None, True, False),
    ids=(
        ".quiet is default -> print prints",
        ".quiet is true -> print does not print",
        ".quiet is false -> print prints",
    ),
)
def test_print_function(capsys, quiet):
    """Checks that the print function is suppressed <=> quiet is set to True"""
    s = StateConfig()
    if quiet is not None:
        s.quiet = quiet
    else:
        assert not s.quiet
    s.print_function("Output")
    captured = capsys.readouterr()
    assert (captured.out == "Output\n") == (not s.quiet)


@pytest.mark.parametrize(
    "filter_mode",
    (None, True, False),
    ids=(
        "filter_mode is default -> prompt and confirm work",
        "filter_mode is true -> Exception",
        "filter_mode is false -> prompt and confirm work",
    ),
)
def test_prompt_function(monkeypatch, filter_mode):
    s = StateConfig()
    if filter_mode is not None:
        s.filter_mode = filter_mode
    else:
        assert not s.filter_mode
    setup_input(monkeypatch, cli_input=("Y", "Y"))

    if s.filter_mode:
        with pytest.raises(Exception):
            s.prompt_function("Prompt?")
        with pytest.raises(Exception):
            s.confirm_function("Prompt?")
    else:
        _ = s.prompt_function("Prompt?")
        assert _ == "Y"
        _ = s.confirm_function("Prompt?")
        assert _
