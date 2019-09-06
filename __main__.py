""" Supplementary script for writing confluence wiki articles in
vim. After specifying page details in the config.json file and posting file's
contents to replace the specified page's content.

Unless --force is specified — checks if the last author is not the one in
"author_to_check" from config.
"""
import logging
from atlassian import Confluence
import argparse
import json
import sys
import pathlib

"""Links:
* https://atlassian-python-api.readthedocs.io/en/latest/
* https://github.com/atlassian-api/atlassian-python-api
"""


def update_page_with_content(file_with_content, page_id, title,
                             confluence_instance):
    with open(file_with_content, 'r') as file_contents:
        confluence_instance.update_page(page_id, title, file_contents.read(),
                                        parent_id=None,
                                        type='page', representation='wiki',
                                        minor_edit=False)


def create_under_parent(space, confluence_instance):
    find_parent = input("Do you want to look for parent page "
                        f"in the space \"{space}\"? (Y/N/(A)bort) ")
    if find_parent.lower() == 'y':
        cont = True
        while cont:
            parent_name = input("Which page should the script "
                                "look for?\n")
            if confluence_instance.page_exists(space,
                                               parent_name):
                parent_id = confluence_instance.get_page_id(space, parent_name)
                return parent_id
            else:
                c = input(f"Did not find page by '{parent_name}'. "
                          "Search again? (Y/N) ")
                if c.lower() == 'y':
                    cont = True
                else:
                    cont = False
    elif find_parent.lower() == "a" or find_parent == "Abort":
        logging.info("Aborting")
    else:
        logging.info("Not creating under a parent")
    return None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json",
                        help="the file with the config")
    parser.add_argument("--password", required=True,
                        help="your confluence password")
    parser.add_argument("--force", help="Force write the page, even if the last\
                        author is different", action='store_true')
    parser.add_argument("--debug", help="Enable debug logging",
                        action='store_true')
    parser.add_argument("--page_title", help="Allows overriding page title from\
                        config")
    parser.add_argument("--upload_files", nargs="+",
                        help="Filenames to upload as "
                        "attachments to page_title")
    return(parser.parse_args())


def main():
    args = parse_args()
    if not args.debug:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s')
    else:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')

    logging.info("Checking config")

    with open(args.config, 'r') as config_file:
        poster_config = json.load(config_file)

    logging.info("Starting Confluence poster")
    if poster_config["auth"]["is_cloud"]:
        api_version = "cloud"
    else:
        api_version = "latest"
    confluence = Confluence(
        url=poster_config["auth"]["confluence_url"],
        username=poster_config["auth"]["username"],
        password=args.password,
        api_version=api_version
    )
    # Check the page_title in args
    if args.page_title:
        title = args.page_title
    else:
        title = poster_config["page"]["title"]

    logging.debug("Looking for the page")
    space = poster_config["page"]["space"]
    if confluence.page_exists(space, title):
        pass
    else:
        create = input(f"Page not found. Create page called {title} in space "
                       f"{space}? (Y/N) ")
        if create.lower() == 'y':
            # TODO: suboptimal metohd, page is updated later
            parent_id = create_under_parent(space, confluence)
            confluence.create_page(space, title, body="", parent_id=parent_id)
        elif create.lower() == 'n':
            logging.info("OK. exiting")
            sys.exit()
        else:
            logging.info("Assuming no, exiting")
            sys.exit()

    page_id = confluence.get_page_id(poster_config["page"]["space"], title)
    logging.debug(f"Found the page {page_id}")

    # Check if the page was modified last by AUTHOR_TO_CHECK. If not - error
    if not args.force:
        page_update = confluence.get_page_by_id(page_id, expand="version")
        if api_version == 'cloud':
            last_updated_by = page_update['version']['by']['email']
        else:
            last_updated_by = page_update['version']['by']['username']

        if last_updated_by != poster_config["author_to_check"]:
            logging.error(f"Last author is not \
{poster_config['author_to_check']}, it's {last_updated_by}")
            logging.error(f"Please check\
{poster_config['auth']['confluence_url']}\
/pages/viewpreviousversions.action?pageId={page_id}")
            logging.error("Aborting")
            sys.exit()
        else:
            logging.info(f"Checked last author, it's {last_updated_by}, like "
                         "in config, proceeding")

    # Update the page with contents from FILE_TO_OPEN
    logging.info("Updating the page")
    try:
        update_page_with_content(poster_config["file_to_open"], page_id,
                                 title, confluence)
    except Exception as e:
        logging.exception(e)
    else:
        logging.info("Update OK")
    if args.upload_files:
        logging.info("Uploading the files")
        for file in args.upload_files:
            logging.info(f"\tUploading file {file}")
            uploaded_file_path = pathlib.Path(file)
            confluence.attach_file(uploaded_file_path,
                                   name=uploaded_file_path.name,
                                   content_type=None, page_id=page_id)
            logging.info(f"\tDone uploading file {file}")
        logging.info("Done upload")


if __name__ == "__main__":
    main()
