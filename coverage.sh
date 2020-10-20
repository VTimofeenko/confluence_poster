#!/bin/sh
python -m pytest -s --cov=confluence_poster/ --cov-report term-missing --cov-config=.coveragerc
