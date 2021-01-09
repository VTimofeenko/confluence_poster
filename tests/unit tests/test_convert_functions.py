import pytest
from confluence_poster.convert_utils import (
    post_to_convert_api,
    convert_using_markdown_lib,
)
from utils import confluence_instance

pytestmark = pytest.mark.online

md_text = "# Title\n* One\n* Two"


@pytest.mark.parametrize(
    "text,exception",
    ((md_text, False),),
    ids=[
        "Post good markdown - get result",
    ],
)
def test_post_to_convert_api(text, exception):
    assert (
        post_to_convert_api(confluence=confluence_instance, text=text)
        == "<h1>Title</h1> <ul> <li>One <li>Two </ul> "
    )


def test_convert_using_markdown_lib():
    assert (
        convert_using_markdown_lib(md_text)
        == """<h1>Title</h1>
<ul>
<li>One</li>
<li>Two</li>
</ul>"""
    )
