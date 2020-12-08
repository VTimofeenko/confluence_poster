from setuptools import setup, find_packages

setup(
    name='confluence_poster',
    version='1.0.0',
    url='https://github.com/SabbathHex/confluence_poster',
    license='MIT',
    author='Vladimir Timofeenko',
    author_email='maintain@vtimofeenko.com',
    include_package_data=True,
    package_data={'': ['config.toml']},
    packages=find_packages(exclude=("tests", "docs")),
    package_dir={'confluence_poster': 'confluence_poster'},
    entry_points={"console_scripts": ["confluence_poster = confluence_poster.main:app"]},
    install_requires=[
        "atlassian-python-api>=1.17.6",
        "typer>=0.3.2",
        "toml",
        "requests"
    ],
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    tests_require=[
        "pytest",
        "pytest-cov",
        "faker"
    ],
    extras_require={
        "docs": [
            'jinja2',
            'typer-cli'
        ]
    },
    description='Script that updates Confluence articles from files written locally',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License"
    ]
)
