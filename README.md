# Description

Supplementary script for writing confluence wiki articles in vim. Capable of alerting in case name of the last author is not the same one as in config so as to prevent collisions in versions.

# Usage

1. Copy `config.json.dict` file contents into the directory with the text file
2. Fill in the blanks of the config file
3. Run 

		# post_to_confluence --password ${PASSWORD}

## Parameters

* `--password PASSWORD` — your confluence password
* `--config CONFIG` — the file with the config by default - config.json in the same folder
* `--force` — Force write the page, even if the last author is different from one specified in `author_to_check`
* `--page_title PAGE_TITLE` — Allows overriding page title from config
* `--upload_files UPLOAD_FILES [UPLOAD_FILES ...]` — Filenames to upload as attachments to `page_title`
* `--debug` — Enable debug logging

## Config

Commented config:

	{
		"file_to_open": "",			# the name of text file with page contents
		"auth" : {
			"confluence_url": "",	# URL of confluence instance
			"username": "",			# usernmae for authentication
			"password": "",			# password
			"is_cloud": false		# see below
		},
		"author_to_check": "",		# if the page was not updated by the username specified here, throw an error
		"page" : {
			"title": "",			# specify page title
			"space": ""}			# specify page space
	}

For copy-pasting purposes, file is [here](https://raw.githubusercontent.com/SabbathHex/confluence_poster/master/config.json.dist).

### `password`

It is probably a bad idea to have the password configured in a random file on the filesystem, so it is recommended to use this script with some external password manager, like [Passwordstore](https://www.passwordstore.org/). The script usage then becomes:

	# post_to_confluence --password $(pass PATH_TO_PASSWORD_OR_TOKEN)

### `is_cloud`

This parameter defines some parts of the script's behavior, namely authentication and the way page edit history is treated. 

Password works differently for online confluence. Follow [this link](https://confluence.atlassian.com/cloud/api-tokens-938839638.html) and generate a token. Use in place of password.

# Installation

Download and install from [releases page](https://github.com/SabbathHex/confluence_poster/releases).

Alternatively, this package is available from [nitratesky](https://github.com/SabbathHex/nitratesky) overlay.

# Building

Python's [zipapp](https://docs.python.org/3/library/zipapp.html) is used to build the "binary", see `build.sh` contents.

# See also

* [Vim confluencewiki syntax](https://www.vim.org/scripts/script.php?script_id=1994)
* [Atlassian python API](https://atlassian-python-api.readthedocs.io/en/latest/) (On [Github](https://github.com/atlassian-api/atlassian-python-ap))

