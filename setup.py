from io import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="x1e2-custodian",
    version="0.1.0",
    description="CPU Frequency Management Daemon and Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lainproliant/x1e2-custodian",
    author="Lain Musgrove",
    author_email="lain.proliant@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="CPU power-management power daemon systemd",
    # packages=find_packages(exclude=["contrib", "docs", "tests"]),  # Required
    py_modules=['readout'],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4",
    install_requires=[
        "ansilog==1.6",
        "click==7.1.2",
        "lexex==1.0.0",
        "psutil==5.7.2",
        "readout==0.1.1",
    ],
    extras_require={"dev": []},
    dependency_links=[],
    project_urls={
        "Bug Reports": "https://github.com/pypa/sampleproject/issues",
        "Funding": "https://donate.pypi.org",
        "Say Thanks!": "http://saythanks.io/to/example",
        "Source": "https://github.com/pypa/sampleproject/",
    },
    entry_points={"console_scripts": ['x1e2=x1e2_custodian:main']}
)
