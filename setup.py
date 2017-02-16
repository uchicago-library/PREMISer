from setuptools import setup, find_packages

def readme():
    with open("README.md", 'r') as f:
        return f.read()

setup(
    name = "premiser",
    description = "An RPC-like endpoint for producing PREMIS records",
    long_description = readme(),
    packages = find_packages(
        exclude = [
        ]
    ),
    dependency_links = [
        'https://github.com/uchicago-library/uchicagoldr-premiswork' +
        '/tarball/master#egg=pypremis',
        'https://github.com/bnbalsamo/nothashes' +
        '/tarball/master#egg=nothashes'
    ],
    install_requires = [
        'flask',
        'flask_restful',
        'pypremis',
        'nothashes'
    ],
)
