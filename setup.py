from setuptools import setup

setup(
    name='confluence_poster',
    version='0.2',
    packages=['confluence_poster'],
    install_requires=[
        "atlassian-python-api>=1.15.7vi"
    ],
    url='https://github.com/SabbathHex/confluence_poster',
    license='MIT',
    author='SabbathHex',
    author_email='sh@93546bd8-f8c4-40e9-a27a-3bd09ba47648',
    description='Supplementary script for writing confluence wiki articles in vim'
)
