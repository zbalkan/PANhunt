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

## Function

The script uses regular expressions to look for Visa, MasterCard or AMEX credit card numbers in document files. Zip files are recursed to look for document files. PST and MSG files are parsed and emails and attachments searched in.

The script will list but does not yet search Access databases.
## Breaking changes

This for includes a full architectural change to allow extending the scanning capabilities by providing a new scanner. It is more modular and has more file searching capabilities. It means there is a performance impact for the sake of accuracy.

With v1.3, breaking changes are implemented:

- Migrated to Python 3
- Used file type detection via `python-magic` instead of depending on file extensions only.
- A default text log capability is added for the sake of accountability.
- Text report now accepts only directory as an argument while the name is fixed.
  - Text report filename template: `panhunt_<timestamp>.report`
- An optional JSON formatted report generation capability is added for integration with 3rd parties. Parameter accepts the target directory.
  - JSON report filename template: `panhunt_<timestamp>.json`
- A flag `-q` (quiet) is added to disable terminal output be used when it is integrated with other tools.
- A flag `-f` (filepath) is added to enable sigle-file scans. Great for FIM integration.
- `.eml` and `.mbox` file scanning capability is added.
- PDF file scanning capability is added. OCR is not working as expected yet.

With v1.4, breaking changes are implemented:
- Removed file extension based filtering. Now it relies on `magic` results.


NB! There is at least 20% performance impact after refactoring. There are no performance improvements tried yet.

## Build

PANhunt is a Python script that can be easily converted to a standalone Windows executable using PyInstaller.

panhunt.py requires:

	- Python 3.6+
	- Colorama (https://pypi.python.org/pypi/colorama)
	- Progressbar (https://pypi.python.org/pypi/progressbar)

You can use `pip install -r requirements.txt` for usage and `pip install -r requirements.dev.txt` for development.

To compile as an executable, it requires:

	- PyInstaller (https://pypi.python.org/pypi/PyInstaller)

In order to create panhunt as a standalone executable run (works in both Linux and Windows):

```bash
pyinstaller panhunt.py -F
```

However, you are advised  use a virtual environment. Update the path on the `build.sh` or `build.bat` file and run. With the short scripts, you can clean the cache, include the original icon and the dependencies (works in both Linux and Windows). The example uses a virtual environment in a folder called `.venv`.

## Usage

```
usage: panhunt [-h] [-s SEARCH_DIR] [-f FILE_PATH] [-x EXCLUDE_DIRS] [-o REPORT_DIR] [-j JSON_DIR] [-u] [-C CONFIG] [-X EXCLUDE_PAN] [-q]

PAN Hunt v1.3: search directories and sub directories for documents containing PANs.

options:
  -h, --help        show this help message and exit
  -s SEARCH_DIR     base directory to search in (default: /)
  -f FILE_PATH      File path for single file scan (default: None)
  -x EXCLUDE_DIRS   directories to exclude from the search (default: C:\Windows,C:\Program Files,C:\Program Files (x86),/mnt,/dev,/proc)
  -o REPORT_DIR     Report file directory for TXT formatted PAN report (default: ./)
  -j JSON_DIR       Report file directory for JSON formatted PAN report (default: None)
  -u                unmask PANs in output (default: False)
  -C CONFIG         configuration file to use (default: None)
  -X EXCLUDE_PAN    PAN to exclude from search (default: None)
  -q                No terminal output (default: False)
```

Simply running it with no arguments will search the `C:\` drive on Windows and filesystem under `/` on Linux, for documents containing PANs, and output to panhunt_<timestamp>.txt.

## Example Output

```
Doc Hunt: 100% |||||||||||||||||||||||||||||||||||||||||| Time: 0:00:00 Docs:11
PAN Hunt: 100% ||||||||||||||||||||||||||||||||||||||||| Time: 0:00:00 PANs:592
FOUND PANs: c:\TEST\PANhunt_Test_File.docx (37.1640625KB 06/04/2023)
        word/document.xml Mastercard:541111******1115
        word/document.xml Mastercard:551111******1114
        word/document.xml Visa:453211******1112
        word/document.xml Visa:475127******1118
        word/document.xml AMEX:371111*****1114
        word/document.xml AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.eml (287.6552734375KB 11/04/2023)
        PAN TEST.txt Mastercard:541111******1115
        PAN TEST.txt Mastercard:551111******1114
        PAN TEST.txt Visa:453211******1112
        PAN TEST.txt Visa:475127******1118
        PAN TEST.txt AMEX:371111*****1114
        PAN TEST.txt AMEX:340000*****0108
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:541111******1115
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:551111******1114
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:453211******1112
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:475127******1118
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:371111*****1114
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:340000*****0108
        TEST.zip\PAN TEST.docx\word/document.xml Mastercard:541111******1115
        TEST.zip\PAN TEST.docx\word/document.xml Mastercard:551111******1114
        TEST.zip\PAN TEST.docx\word/document.xml Visa:453211******1112
        TEST.zip\PAN TEST.docx\word/document.xml Visa:475127******1118
        TEST.zip\PAN TEST.docx\word/document.xml AMEX:371111*****1114
        TEST.zip\PAN TEST.docx\word/document.xml AMEX:340000*****0108
        TEST.zip\PAN TEST.rtf Mastercard:541111******1115
        TEST.zip\PAN TEST.rtf Mastercard:551111******1114
        TEST.zip\PAN TEST.rtf Visa:453211******1112
        TEST.zip\PAN TEST.rtf Visa:475127******1118
        TEST.zip\PAN TEST.rtf AMEX:371111*****1114
        TEST.zip\PAN TEST.rtf AMEX:340000*****0108
        TEST.zip\PAN TEST.txt Mastercard:541111******1115
        TEST.zip\PAN TEST.txt Mastercard:551111******1114
        TEST.zip\PAN TEST.txt Visa:453211******1112
        TEST.zip\PAN TEST.txt Visa:475127******1118
        TEST.zip\PAN TEST.txt AMEX:371111*****1114
        TEST.zip\PAN TEST.txt AMEX:340000*****0108
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:541111******1115
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:551111******1114
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Visa:453211******1112
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Visa:475127******1118
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml AMEX:371111*****1114
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml AMEX:340000*****0108
        PAN TEST.docx\word/document.xml Mastercard:541111******1115
        PAN TEST.docx\word/document.xml Mastercard:551111******1114
        PAN TEST.docx\word/document.xml Visa:453211******1112
        PAN TEST.docx\word/document.xml Visa:475127******1118
        PAN TEST.docx\word/document.xml AMEX:371111*****1114
        PAN TEST.docx\word/document.xml AMEX:340000*****0108
        PAN TEST.rtf Mastercard:541111******1115
        PAN TEST.rtf Mastercard:551111******1114
        PAN TEST.rtf Visa:453211******1112
        PAN TEST.rtf Visa:475127******1118
        PAN TEST.rtf AMEX:371111*****1114
        PAN TEST.rtf AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.msg (207.0KB 06/04/2023)
        PAN TEST.txt Mastercard:541111******1115
        PAN TEST.txt Mastercard:551111******1114
        PAN TEST.txt Visa:453211******1112
        PAN TEST.txt Visa:475127******1118
        PAN TEST.txt AMEX:371111*****1114
        PAN TEST.txt AMEX:340000*****0108
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:541111******1115
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:551111******1114
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:453211******1112
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:475127******1118
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:371111*****1114
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:340000*****0108
        TEST.zip\PAN TEST.docx\word/document.xml Mastercard:541111******1115
        TEST.zip\PAN TEST.docx\word/document.xml Mastercard:551111******1114
        TEST.zip\PAN TEST.docx\word/document.xml Visa:453211******1112
        TEST.zip\PAN TEST.docx\word/document.xml Visa:475127******1118
        TEST.zip\PAN TEST.docx\word/document.xml AMEX:371111*****1114
        TEST.zip\PAN TEST.docx\word/document.xml AMEX:340000*****0108
        TEST.zip\PAN TEST.rtf Mastercard:541111******1115
        TEST.zip\PAN TEST.rtf Mastercard:551111******1114
        TEST.zip\PAN TEST.rtf Visa:453211******1112
        TEST.zip\PAN TEST.rtf Visa:475127******1118
        TEST.zip\PAN TEST.rtf AMEX:371111*****1114
        TEST.zip\PAN TEST.rtf AMEX:340000*****0108
        TEST.zip\PAN TEST.txt Mastercard:541111******1115
        TEST.zip\PAN TEST.txt Mastercard:551111******1114
        TEST.zip\PAN TEST.txt Visa:453211******1112
        TEST.zip\PAN TEST.txt Visa:475127******1118
        TEST.zip\PAN TEST.txt AMEX:371111*****1114
        TEST.zip\PAN TEST.txt AMEX:340000*****0108
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:541111******1115
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:551111******1114
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Visa:453211******1112
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml Visa:475127******1118
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml AMEX:371111*****1114
        TEST.zip\PAN TEST.xlsx\xl/sharedStrings.xml AMEX:340000*****0108
        PAN TEST.docx\word/document.xml Mastercard:541111******1115
        PAN TEST.docx\word/document.xml Mastercard:551111******1114
        PAN TEST.docx\word/document.xml Visa:453211******1112
        PAN TEST.docx\word/document.xml Visa:475127******1118
        PAN TEST.docx\word/document.xml AMEX:371111*****1114
        PAN TEST.docx\word/document.xml AMEX:340000*****0108
        PAN TEST.rtf Mastercard:541111******1115
        PAN TEST.rtf Mastercard:551111******1114
        PAN TEST.rtf Visa:453211******1112
        PAN TEST.rtf Visa:475127******1118
        PAN TEST.rtf AMEX:371111*****1114
        PAN TEST.rtf AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.ppt (84.5KB 11/04/2023)
        Mastercard:541111******1115
        Mastercard:551111******1114
        Visa:453211******1112
        Visa:475127******1118
        AMEX:371111*****1114
        AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.pptx (36.0849609375KB 11/04/2023)
        ppt/slides/slide1.xml Mastercard:541111******1115
        ppt/slides/slide1.xml Mastercard:551111******1114
        ppt/slides/slide1.xml Visa:453211******1112
        ppt/slides/slide1.xml Visa:475127******1118
        ppt/slides/slide1.xml AMEX:371111*****1114
        ppt/slides/slide1.xml AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.rtf (42.98046875KB 06/04/2023)
        Mastercard:541111******1115
        Mastercard:551111******1114
        Visa:453211******1112
        Visa:475127******1118
        AMEX:371111*****1114
        AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.txt (685B 04/04/2023)
        Mastercard:541111******1115
        Mastercard:551111******1114
        Visa:453211******1112
        Visa:475127******1118
        AMEX:371111*****1114
        AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.xlsx (9.708984375KB 06/04/2023)
        xl/sharedStrings.xml Mastercard:541111******1115
        xl/sharedStrings.xml Mastercard:551111******1114
        xl/sharedStrings.xml Visa:453211******1112
        xl/sharedStrings.xml Visa:475127******1118
        xl/sharedStrings.xml AMEX:371111*****1114
        xl/sharedStrings.xml AMEX:340000*****0108

FOUND PANs: c:\TEST\PANhunt_Test_File.zip (49.619140625KB 06/04/2023)
        PAN TEST.docx\word/document.xml Mastercard:541111******1115
        PAN TEST.docx\word/document.xml Mastercard:551111******1114
        PAN TEST.docx\word/document.xml Visa:453211******1112
        PAN TEST.docx\word/document.xml Visa:475127******1118
        PAN TEST.docx\word/document.xml AMEX:371111*****1114
        PAN TEST.docx\word/document.xml AMEX:340000*****0108
        PAN TEST.rtf Mastercard:541111******1115
        PAN TEST.rtf Mastercard:551111******1114
        PAN TEST.rtf Visa:453211******1112
        PAN TEST.rtf Visa:475127******1118
        PAN TEST.rtf AMEX:371111*****1114
        PAN TEST.rtf AMEX:340000*****0108
        PAN TEST.txt Mastercard:541111******1115
        PAN TEST.txt Mastercard:551111******1114
        PAN TEST.txt Visa:453211******1112
        PAN TEST.txt Visa:475127******1118
        PAN TEST.txt AMEX:371111*****1114
        PAN TEST.txt AMEX:340000*****0108
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:541111******1115
        PAN TEST.xlsx\xl/sharedStrings.xml Mastercard:551111******1114
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:453211******1112
        PAN TEST.xlsx\xl/sharedStrings.xml Visa:475127******1118
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:371111*****1114
        PAN TEST.xlsx\xl/sharedStrings.xml AMEX:340000*****0108

Report written to panhunt_YYYY-MM-DD-HHMMSS.txt
```

## Configuration

The script allows for a configuration to be written that will default the application with settings such that you don't need to
repeatedly specify exclude/include paths or the test PANs to exclude.