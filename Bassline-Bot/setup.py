"""Setup script for BasslineBot Pro."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="basslinebot-pro",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Professional Discord Music Bot with advanced features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bassline-bot-pro",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/bassline-bot-pro/issues",
        "Documentation": "https://basslinebot.pro/docs",
        "Source Code": "https://github.com/yourusername/bassline-bot-pro",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Multimedia :: Sound/Audio :: Players",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "isort>=5.10.0",
            "mypy>=0.991",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "grafana-api>=1.0.3",
        ],
        "commercial": [
            "stripe>=5.0.0",
            "sendgrid>=6.9.0",
            "celery>=5.2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "basslinebot=src.bot:main",
            "basslinebot-migrate=scripts.migrate:main",
            "basslinebot-backup=scripts.backup:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml", "*.json"],
        "src": ["static/*", "templates/*"],
        "config": ["*.py"],
        "scripts": ["*.py", "*.sh", "*.bat"],
        "docs": ["*.md"],
    },
    keywords="discord bot music youtube audio streaming playlist",
    zip_safe=False,
)