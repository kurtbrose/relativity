from setuptools import setup


__author__ = 'Kurt Rose'
__version__ = '20.1.0'
__contact__ = 'kurt@kurtrose.com'
__url__ = 'https://github.com/kurtbrose/relativity'
__license__ = 'MIT'


with open('README.rst') as readme_f:
    long_description = readme_f.read()



setup(name='relativity',
      version=__version__,
      description="Relational object sets.",
      long_description=long_description,
      long_description_content_type='text/x-rst',
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['relativity', 'relativity.tests'],
      include_package_data=True,
      zip_safe=False,
      license=__license__,
      platforms='any',
      classifiers=[
          'Topic :: Utilities',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Libraries',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy', ]
)


"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump setup.py version off of -dev
* git commit -a -m "bump version for vx.y.z release"
* rm -rf dist/*
* python setup.py sdist bdist_wheel
* twine upload dist/*
* bump docs/conf.py version
* git commit
* git tag -a vx.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump setup.py version onto n+1 dev
* git commit
* git push

"""
