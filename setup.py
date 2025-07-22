from setuptools import setup

if __name__ == "__main__":
    setup()

"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump pyproject.toml version off of -dev
* git commit -a -m "bump version for vx.y.z release"
* rm -rf dist/*
* python -m build
* twine upload dist/*
* bump docs/conf.py version
* git commit
* git tag -a vx.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump pyproject.toml version onto n+1 dev
* git commit
* git push

"""
