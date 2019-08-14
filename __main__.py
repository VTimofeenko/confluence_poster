import logging
from atlassian import Confluence
import argparse
import json

"""
Description: Supplementary script for writing confluence wiki articles in vim
After specifying page details in the Settings file and posting file's contents
to replace the specified page's content

Author: Vladimir Timofeenko

TODO:
    * pass integration for keyring capabilities


"""


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


def update_page_with_content(file_with_content, page_id, title,
                             confluence_instance):
    with open(file_with_content, 'r') as file_contents:
        confluence_instance.update_page(page_id, title, file_contents.read(),
                                        parent_id=None,
                                        type='page', representation='wiki',
                                        minor_edit=False)


def main():
    logging.info("Checking config")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--password")
    args = parser.parse_args()
    with open(args.config, 'r') as config_file:
        poster_config = json.load(config_file)

    logging.info("Starting Confluence poster")
    # Check if the page was modified last by AUTHOR_TO_CHECK. If not - error
    confluence = Confluence(
        url=poster_config["auth"]["confluence_url"],
        username=poster_config["auth"]["username"],
        password=args.password)
    title = poster_config["page"]["title"]
    page_id = confluence.get_page_id(poster_config["page"]["space"], title)
    page_update = confluence.get_page_by_id(page_id, expand="version")
    if page_update['version']['by']['username'] == \
       poster_config["author_to_check"]:
        # Update the page with contents from FILE_TO_OPEN
        logging.info("Updating the page")
        try:
            update_page_with_content(poster_config["file_to_open"], page_id,
                                     title, confluence)
        except Exception as e:
            logging.exception(e)
        else:
            logging.info("Update OK")
    else:
        logging.error(f"Last author is not {poster_config['author_to_check']}")
        logging.error("Aborting")


if __name__ == "__main__":
    main()
