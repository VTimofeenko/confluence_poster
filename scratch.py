from atlassian import Confluence

from confluence_poster.main_helpers import PostedPage
from confluence_poster.poster_config import Config
from confluence_poster.convert_utils import (
    post_to_wiki_convert_api,
    post_to_convert_api,
)

c = Config("local_config.toml")
api_version = "latest"
conf = Confluence(
    url=c.auth.url,
    username=c.auth.username,
    password=c.auth.password,
    api_version=api_version,
)

# page_id = conf.get_page_id(space="LOC", title="TEST")
# p = PostedPage("TEST", "page1.confluencewiki", "LOC", page_id=page_id)

# path = Path("page1.confluencewiki")
# conf.attach_file(str(path), name=path.name, page_id=page_id)
# print("attached")
# conf.delete_attachment(page_id, path.name)
#
# state = StateConfig()
# state.confluence_instance = conf
# attach_files_to_page(page=p, files=[path], state=state)
# conf.delete_attachment(page_id, path.name)

text = "[Text^attachment.ext]"

try:
    print(post_to_wiki_convert_api(confluence=conf, text=text))
except:
    pass
print("TEST")
print(post_to_convert_api(confluence=conf, text=text))
