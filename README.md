# Config

* `is_cloud`: true/false — determines whether tweaks for cloud-based confluence will be used.

	Cloud confluence seems to have different version of `page_update['version']` json, so the last updated username needs to be extracted in a different manner.

# For cloud-based

Follow [this link](https://confluence.atlassian.com/cloud/api-tokens-938839638.html) and generate a token. Use in place of password for cloud-based Confluence
