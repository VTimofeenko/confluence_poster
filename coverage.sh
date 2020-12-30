#!/bin/sh
python -m pytest --show-capture=no --cov=confluence_poster/ --cov-report term-missing --cov-config=.coveragerc
