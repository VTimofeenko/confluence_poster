# Description

Supplementary script for writing confluence wiki articles in
vim. Uses information from the config to post the article content to confluence.

**Usage**:

```console
$ confluence_poster [OPTIONS] COMMAND [ARGS]...
```

**General Options**:

* `--version`: Show version and exit
* `--config PATH`: The file containing configuration. If not specified - config.toml from the same directory is used  [default: config.toml]
* `--page-title TEXT`: Override page title from config. Applicable if there is only one page.
* `--parent-page-title TEXT`: Provide a parent title to search for. Applicable if there is only one page.
* `--password TEXT`: Supply the password in command line.  [env var: CONFLUENCE_PASSWORD]
* `--force`: Force overwrite the pages. Applicable if the author is different.
* `--force-create`: Disable prompts to create pages. Script could still prompt for a parent page.
* `--minor-edit`: Do not notify watchers of pages updates. Not enabled by default.
* `--report`: Print report at the end of the run. Not enabled by default.
* `--debug`: Enable debug logging. Not enabled by default.
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

These options can be specified for any `COMMAND` except for  `create-config` which ignores these options.

**Commands**:

* `create-config`: Runs configuration wizard.
* `post-page`: Posts the content of the pages.
* `validate`: Validates the provided settings.

# Commands
## `confluence_poster post-page`

Posts the content of the pages.

**Usage**:

```console
$ confluence_poster post-page [OPTIONS]
```

**Options**:

* `--upload-files PATH`: Files to upload as attachments to page.
* `--help`: Show this message and exit.

## `confluence_poster validate`

Validates the provided settings. If 'online' is true - tries to fetch the space from the config using the
supplied credentials.

**Usage**:

```console
$ confluence_poster validate [OPTIONS]
```

**Options**:

* `--online`: Test the provided authentication settings on the actual instance of confluence.
* `--help`: Show this message and exit.

## `confluence_poster create-config`

Runs configuration wizard. The wizard guides through setting up values for config.

**Options**:

* `--local-only`: Create config only in the local folder  [default: False]
* `--home-only`: Create config only in the $XDG_CONFIG_HOME  [default: False]
* `--help`: Show this message and exit.

# Installation

Install the project from PyPI:

```console
$ pip install confluence-poster
```

To start using `confluence_poster` either create the config manually or run `confluence_poster create-config` to start
configuration wizard which will guide you through the configuration.

# Config format

By default the confluence_poster tries to look for config file `config.toml` in the directory where it is invoked and in
XDG_CONFIG_HOME. The config format is as follows:

```toml
# If the page was not updated by the username specified here, throw an error.
# If this setting is omitted - username from auth section is used for checks.
author = "author_username"

[pages]
[pages.default]
# Space key. E.g. for space "local-dev" the space key is "LOC"
# Space defined here will be used if a page section below does not specify it
page_space = "DEFAULT_SPACE_KEY"
[pages.page1]
# The title of the page
page_title = "Some page title"
# The filename with page content
page_file = "some_file.confluencewiki"
# If specified - overrides the default page_space
page_space = "some_space_key"

[pages.page2]
page_title = "Some other page title"
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

**Note on password and Cloud instances**: if confluence is hosted by Atlassian, the password is the API token.
Follow instructions at [this link](https://confluence.atlassian.com/cloud/api-tokens-938839638.html).

# Contrib directory

There are shell completions for bash and zsh as well as a sample of
[git post-commit hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks).

# See also

* [Vim confluencewiki syntax](https://www.vim.org/scripts/script.php?script_id=1994)
* [Paste confluence image in vim](https://github.com/SabbathHex/confluencewiki-img-paste.vim)
* [Atlassian python API](https://atlassian-python-api.readthedocs.io/en/latest/) (On [Github](https://github.com/atlassian-api/atlassian-python-api))