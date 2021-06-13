#!/bin/sh

pip freeze > requirements.txt

tox -e clean,py38,py39

