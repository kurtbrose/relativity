from setuptools import setup


__author__ = 'Kurt Rose'
__version__ = '0.1dev'
__contact__ = 'kurt@kurtrose.com'
__url__ = 'https://github.com/kurtbrose/relativity'
__license__ = 'MIT'


setup(name='relativity',
      version=__version__,
      description="Relational object sets.",
      long_description=__doc__,
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
