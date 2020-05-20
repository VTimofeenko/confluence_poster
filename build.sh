#!/bin/sh
# Generates pyz file for the project


# Create building area
[ ! -d "build_area/" ] &&  mkdir build_area
echo "Cleaning build area"
rm -rf build_area/*

# Check for virtual environment. May be a little too obtuse
[ ! -d "lib/" ] && echo "Looks like this is not virtual environment" && exit 1
echo "Copying main executable file to build area"
cp __main__.py build_area/
echo "Copying libs to build area"
cp -r lib/python3.*/site-packages/* build_area/
echo "Clearing __pycache__"
rm -rf build_area/__pycache__/

# Actual build
echo "Building zipapp"
[ ! -d "distribs/" ] && mkdir distribs
python3 -m zipapp build_area/ -o distribs/post_to_confluence -p "/bin/env python3"
echo "Copying config dist"
cp -f config.json.dist distribs/
