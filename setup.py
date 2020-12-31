from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name="confluence_poster",
    version="1.2.0",
    description="Script that updates Confluence articles from files written locally",
    long_description=(here / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/VTimofeenko/confluence_poster",
    license="MIT",
    author="Vladimir Timofeenko",
    author_email="confluence.poster.maintain@vtimofeenko.com",
    include_package_data=True,
    package_data={"confluence_poster": ["config.toml"]},
    packages=find_packages(exclude=("tests", "docs")),
    package_dir={"confluence_poster": "confluence_poster"},
    entry_points={
        "console_scripts": ["confluence_poster = confluence_poster.main:app"]
    },
    install_requires=[
        "atlassian-python-api==2.3.0",
        "typer>=0.3.2",
        "toml",
        "requests",
        "xdg>=5.0.1",
        "tomlkit==0.7.0",
    ],
    python_requires=">=3.8, <4",
    tests_require=["pytest", "pytest-cov", "faker"],
    extras_require={"docs": ["jinja2", "typer-cli"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Topic :: Utilities",
        "Topic :: Text Processing",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="confluence api vim",
    project_urls={
        "Bug Reports": "https://github.com/VTimofeenko/confluence_poster/issues",
        "Source": "https://github.com/VTimofeenko/confluence_poster/",
    },
)
