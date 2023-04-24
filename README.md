# PANhunt

[![Bandit](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml)
[![CodeQL](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml)
[![DevSkim](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml)

## Introduction

```
NOTE: This is a fork of original PANHunt as an effort to migrate to Python 3.
It is heavily modified and refactored. There may be issues with functionality. Do not use in production!
```

PANhunt is a tool that can be used to search drives for credit card numbers (PANs). This is useful for checking PCI DSS scope accuracy. It's designed to be a simple, standalone tool that can be run from a USB stick. PANhunt includes a python PST file parser.

With v1.3, breaking changes are implemented:

- Migrated to Python 3
- A default text log appended for the sake of accountability
- Text report now accepts only directory as an argument while the name is fixed.
  - Text report filename template: `panhunt_<timestamp>.report`
- An optional JSON formatted report generation capability is added for integration with 3rd parties.
  - JSON report filename template: `panhunt_<timestamp>.json`
- A flag `-q` (quiet) is added to disable terminal output be used when it is integrated with other tools.

NB! There is around 20-25% performance impact after refactoring. There are no performance improvements tried yet.

## Build

PANhunt is a Python script that can be easily converted to a standalone Windows executable using PyInstaller.

panhunt.py requires:

	- Python 3.6+
	- Colorama (https://pypi.python.org/pypi/colorama)
	- Progressbar (https://pypi.python.org/pypi/progressbar)

You can use `pip install -r requirements.txt` for usage and `pip install -r requirements.dev.txt` for development.

To compile as an executable:

	- PyInstaller (https://pypi.python.org/pypi/PyInstaller)

To create panhunt.exe as a standalone executable run:

```bash
pyinstaller.exe panhunt.py -F
```

or you can use this to include the icon and your virtual environment

```bash
pyinstaller.exe panhunt.py -F --clean -i .\dionach.ico --paths="<path to virtual env>\Lib\site-packages"
```

## Usage

```
usage: panhunt [-h] [-s SEARCH] [-x EXCLUDE] [-t TEXT_FILES] [-z ZIP_FILES] [-e SPECIAL_FILES] [-m MAIL_FILES] [-l OTHER_FILES]
               [-o REPORT_DIR] [-j JSON_DIR] [-u] [-C CONFIG] [-X EXCLUDE_PAN] [-q]

PAN Hunt v1.3: search directories and sub directories for documents containing PANs.

options:
  -h, --help        show this help message and exit
  -s SEARCH         base directory to search in (default: /)
  -x EXCLUDE        directories to exclude from the search (default: None)
  -t TEXT_FILES     text file extensions to search (default:
                    .doc,.xls,.ppt,.xml,.txt,.csv,.log,.rtf,.tmp,.bak,.rtf,.csv,.htm,.html,.js,.css,.md,.json)
  -z ZIP_FILES      zip file extensions to search (default: .docx,.xlsx,.pptx,.zip)
  -e SPECIAL_FILES  special file extensions to search (default: .msg)
  -m MAIL_FILES     email file extensions to search (default: .pst)
  -l OTHER_FILES    other file extensions to list (default: .ost,.accdb,.mdb)
  -o REPORT_DIR     Report file directory for TXT formatted PAN report (default: ./)
  -j JSON_DIR       Report file directory for JSON formatted PAN report (default: None)
  -u                unmask PANs in output (default: False)
  -C CONFIG         configuration file to use (default: None)
  -X EXCLUDE_PAN    PAN to exclude from search (default: None)
  -q                No terminal output (default: False)
```

Simply running it with no arguments will search the C:\ drive for documents containing PANs, and output to panhunt_<timestamp>.txt.

## Example Output

```
Doc Hunt: 100% ||||||||||||||||||||||||||||||||||||||||| Time: 0:00:01 Docs:299
PAN Hunt: 100% |||||||||||||||||||||||||||||||||||||||||| Time: 0:00:02 PANs:99
FOUND PANs: D:\lab\Archive Test Cards.zip (21KB 19/02/2014)
        Archived Test Cards Excel 97-2003.xls AMEX:***********0005
        Archived Test Cards Excel 97-2003.xls AMEX:***********8431
		...
FOUND PANs: D:\lab\Archived Test Cards Word 2010.docx (19KB 18/02/2014)
        word/document.xml Visa:************1111
        word/document.xml Visa:************1881
        word/document.xml Visa:************1111
        word/document.xml Visa:************0000
		...
FOUND PANs: D:\lab\test card text file.txt (47B 26/02/2014)
         Visa:************1111
         Visa:****-****-****-1111
		...
Report written to panhunt_YYYY-MM-DD-HHMMSS.txt
```

## Function

The script uses regular expressions to look for Visa, MasterCard or AMEX credit card numbers in document files. Zip files are recursed to look for document files. PST and MSG files are parsed and emails and attachments searched in. The script will list but does not yet search Access databases.

## Configuration

The script allows for a configuration to be written that will default the application with settings such that you don't need to
repeatedly specify exclude/include paths or the test PANs to exclude.

## TODO

- Automate pyinstaller releases with Github actions
- Use generics
- Proper logging
- Multithreading
- Unit tests