from atlassian import Confluence


def post_to_convert_api(confluence: Confluence, text: str) -> str:
    url = "rest/tinymce/1/markdownxhtmlconverter"
    # the endpoint returns plain text, need to redefine the default header
    headers = {"Content-Type": "application/json"}
    # Keep until https://github.com/atlassian-api/atlassian-python-api/pull/684 is merged
    original_advanced_mode = confluence.advanced_mode
    if confluence.advanced_mode is False or confluence.advanced_mode is None:
        confluence.advanced_mode = True

    response = confluence.post(url, data={"wiki": text}, headers=headers)

    confluence.advanced_mode = original_advanced_mode

    return response.text
