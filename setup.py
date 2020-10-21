from setuptools import setup

setup(
    name='confluence_poster',
    version='1.0',
    packages=['confluence_poster'],
    package_dir={'': 'tests'},
    url='https://github.com/SabbathHex/confluence_poster',
    license='MIT',
    author='SabbathHex',
    author_email='',
    include_package_data=True,
    entry_points={"console_scripts": ["confluence_poster = confluence_poster"]},
    install_requires=[
        "atlassian-python-api>=1.17.6",
        "typer>=0.3.2",
        "toml"
    ],
    long_description=open("README.md").read(),
    tests_require=[
        "pytest",
        "pytest-cov",
        "Faker"
    ],
    description='Script that updates Confluence articles from files written locally',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License"
    ]
)
