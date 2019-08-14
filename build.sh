#!/bin/sh

# Generates pyz file for the project
[ ! -d "build_area/" ] &&  mkdir build_area
echo "Cleaning build area"
rm -rf build_area/*
echo "Copying main executable file to build area"
cp __main__.py build_area/
echo "Copying libs to build area"
cp -r lib/python3.6/site-packages/* build_area/
echo "Clearing __pycache__"
rm -rf build_area/__pycache__/

echo "Building zipapp"
python3.6 -m zipapp build_area/ -o distribs/post_to_confluence -p "python3.6"

echo "Copying config dist"
cp -f config.json.dist distribs/
