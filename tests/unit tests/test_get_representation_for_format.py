import pytest
from confluence_poster.convert_utils import (
    Representation,
    get_representation_for_format,
)
from confluence_poster.poster_config import AllowedFileFormat

pytestmark = pytest.mark.offline

arg_values = (
    (AllowedFileFormat.markdown, Representation.editor, False),
    (AllowedFileFormat.confluencewiki, Representation.wiki, False),
    (AllowedFileFormat.html, Representation.editor, False),
    (AllowedFileFormat.none, "", True),
    ("SomeString", "", True),
)


ids = map(
    lambda _: f"Representation: {_[0]} -> {_[1]}{' with exception' * _[2]}", arg_values
)


@pytest.mark.parametrize(
    argnames=("file_format", "representation", "exception"),
    argvalues=arg_values,
    ids=ids,
)
def test_get_representation_for_format(file_format, representation, exception):
    if exception:
        with pytest.raises(ValueError):
            get_representation_for_format(file_format)
    else:
        assert get_representation_for_format(file_format) == representation
