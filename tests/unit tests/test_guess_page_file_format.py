import pytest
from confluence_poster.convert_utils import guess_file_format
from confluence_poster.poster_config import AllowedFileFormat

pytestmark = pytest.mark.offline

arg_values = (
    ("file.md", AllowedFileFormat.markdown, False),
    ("file.confluencewiki", AllowedFileFormat.confluencewiki, False),
    ("file.html", AllowedFileFormat.html, False),
    ("file.docx", AllowedFileFormat.none, True),
)
ids = map(lambda _: f"Filename: {_[0]} -> {_[1]}{' with exception' * _[2]}", arg_values)


@pytest.mark.parametrize(
    argnames=("filename", "file_format", "exception"),
    argvalues=arg_values,
    ids=ids,
)
def test_file_format(filename, file_format, exception):
    if exception:
        with pytest.raises(ValueError):
            guess_file_format(filename)
    else:
        assert guess_file_format(filename) == file_format
