"""
Setup configuration for Nagini Programming Language
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nagini-lang",
    version="0.2.0",
    author="Nagini Development Team",
    description="A compiled, Python-inspired programming language with hybrid memory management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Hammurabi/Nagini",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Compilers",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "nagini=nagini.cli:main",
        ],
    },
    include_package_data=True,
)
