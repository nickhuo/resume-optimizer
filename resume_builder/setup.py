#!/usr/bin/env python3
"""
Setup script for Semi-Apply Resume Builder
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Semi-Apply Resume Builder - LLM Resume Data Validator"

# Define requirements for resume validator
def get_requirements():
    """Return the core requirements for resume validator"""
    return [
        "jsonschema>=4.19.0",  # For JSON schema validation
    ]

setup(
    name="semi-apply-resume-builder",
    version="1.0.0",
    description="LLM Resume Data Validator for PDF rendering requirements",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Nick Huo",
    author_email="jiajunhuo726@gmail.com",
    url="https://github.com/nickhuo/semi-apply",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=get_requirements(),
    entry_points={
        'console_scripts': [
            'validate-resume=cli.validate_resume:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Office/Business",
    ],
    keywords="resume validator llm pdf automation",
    project_urls={
        "Bug Reports": "https://github.com/nickhuo/semi-apply/issues",
        "Source": "https://github.com/nickhuo/semi-apply",
    },
)
