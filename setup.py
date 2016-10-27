from setuptools import setup, find_packages

setup(
    name="backup-excluder",

    version="1.0.0",

    description="Simple GUI to estimate the size of backups.",

    long_description="""
Minimal GUI useful to manage lists of files to exculde from backups.

Visually depicts the size of folders/items, which folders/items
are being excluded, which folders contains excluded files. Regex
can be used to exclude files and folders following a pattern (e.g.,
.*\.py[cod]). Exports all excluded (also derived from regex) files
and folders absolute path in a text file that can be used in a
backup program.""",

    url="https://github.com/develersrl/backup-excluder",

    author="Develer",

    author_email="",

    license="GPL-3.0",

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Archiving :: Backup"
    ],

    keywords="backup",

    py_modules=["backup_excluder", "model", "scripts.dirsize"],

    #install_requires=[],

    extras_require={
       "qt": ["PyQt5"]
    },

    entry_points={
        "console_scripts": [
            "bex = backup_excluder:main"
        ]
    }

)
