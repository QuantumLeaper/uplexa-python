# -*- coding: utf-8 -*-
import codecs
import os
import re
from distutils.core import setup

from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))


def find_version(*parts):
    """
    Figure out version number without importing the package.
    https://packaging.python.org/guides/single-sourcing-package-version/
    """
    with codecs.open(os.path.join(here, *parts), 'r', errors='ignore') as fp:
        version_file = fp.read()
    version_match = re.search(r"^__version__ = ['\"](.*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


version = find_version('uplexa', '__init__.py')

setup(
    name = 'uplexa-python',
    version = version,
    description = 'A comprehensive Python module for handling uPlexa cryptocurrency',
    url = 'https://github.com/uplexa/uplexa-python/',
    long_description = open('README.rst', 'rb').read().decode('utf-8'),
    install_requires = open('requirements.txt', 'r').read().splitlines(),
    tests_require=open('test_requirements.txt', 'r').read().splitlines(),
    setup_requires=[
        'pytest-runner',
    ],
    packages = find_packages('.', exclude=['tests']),
    include_package_data = True,
    author = 'Michał Sałaban',
    author_email = 'michal@salaban.info',
    license = 'BSD-3-Clause',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords = 'uplexa cryptocurrency',
    test_suite='tests',
)
