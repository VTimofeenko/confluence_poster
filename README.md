# Description

Supplementary script for writing confluence wiki articles in
vim. Uses information from config.toml to post the article content to confluence.

**Usage**:

```console
$ confluence_poster [OPTIONS] COMMAND [ARGS]...
```

**General Options**:

* `--config TEXT`: The file containing configuration.  [default: config.toml]
* `--page-title TEXT`: Override page title from config. Applicable if there is only one page.
* `--parent-page-title TEXT`: Provide a parent title to search for. Applicable if there is only one page.
* `--password TEXT`: Supply the password in command line.  [env var: CONFLUENCE_PASSWORD]
* `--force / --no-force`: Force overwrite the pages. Applicable if the author is different.  [default: False]
* `--minor-edit / --no-minor-edit`: Do not notify watchers of pages updates  [default: False]
* `--report / --no-report`: Print report at the end of the run  [default: False]
* `--debug / --no-debug`: Enable debug logging.  [default: False]
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

These options can be specified for any `COMMAND`.

**Commands**:

* `post-page`: Posts the content of the pages.
* `upload-files`: Uploads the provided files.
* `validate`: Validates the provided settings.

# Commands
## `confluence_poster post-page`

Posts the content of the pages.

**Usage**:

```console
$ confluence_poster post-page [OPTIONS]
```

**Options**:

* `--force-create / --no-force-create`: Disable prompts to create pages. Script could still prompt for a parent page.  [default: False]
* `--help`: Show this message and exit.

## `confluence_poster upload-files`

Uploads the provided files.

**Usage**:

```console
$ confluence_poster upload-files FILES...
```

**Arguments**:

* `FILES...`: Files to upload.  [required]

## `confluence_poster validate`

Validates the provided settings. If 'online' is true - tries to fetch the space from the config using the
supplied credentials.

**Usage**:

```console
$ confluence_poster validate [OPTIONS]
```

**Options**:

* `--online / --no-online`: Test the provided authentication settings on the actual instance of confluence.  [default: False]
* `--help`: Show this message and exit.

# Installation

Currently the project is installable through

```console
$ pip install TODO
```

# Config format

Config file `config.toml` should be located in the directory where the confluence_poster is invoked. The format is as follows:

```toml
# If the page was not updated by the username specified here, throw an error.
# If this setting is omitted - auth.username is used for checks.
author = "author_username"

[pages]
[pages.default]
# Space should be defined as abbreviation, otherwise 403 error would be generated
page_space = "default space"
[pages.page1]
page_title = "Some page name"
# The name of text file with page contents
page_file = "some_file.confluencewiki"
# If specified - overrides the default page_space
page_space = "some_space"

[pages.page2]
page_title = "Some other page name"
page_file = "some_other_file.confluencewiki"

[auth]
# URL of confluence instance
confluence_url = "https://confluence.local"
# Username for authentication
username = "confluence_username"
# Password may also be supplied through --password option or from an environment variable CONFLUENCE_PASSWORD
password = "confluence_password"
# Whether the confluence instance is a "cloud" one
is_cloud = false

```

**Note on password and Cloud instances**: if confluence is hosted by Atlassian, the password is the API token. Follow instructions at [this link](https://confluence.atlassian.com/cloud/api-tokens-938839638.html).

# Contrib directory

There are shell completions for bash and zsh as well as a sample of [git post-commit hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks).
