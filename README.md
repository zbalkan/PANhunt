# PANhunt

[![Bandit](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml)
[![CodeQL](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml)
[![DevSkim](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml)

## Introduction

```shell
NOTE: This is a fork of original PANHunt as an effort to migrate to Python 3.
It is heavily modified and refactored. There may be issues with functionality. Do not use in production!
```

PANhunt is a tool that can be used to search drives for credit card numbers (PANs). This is useful for checking PCI DSS scope accuracy. It's designed to be a simple, standalone tool that can be run from a USB stick. PANhunt includes a python PST file parser.

## Function

The script uses regular expressions to look for Visa, MasterCard or AMEX credit card numbers in document files. Zip files are recursed to look for document files. PST and MSG files are parsed and emails and attachments searched in.

The script will list but does not yet search Access databases.

## Build

PANhunt is a Python script that can be easily converted to a standalone Windows executable using PyInstaller.

panhunt.py requires:

- Python 3.9

You can use `pip install -r requirements.txt` for usage and `pip install -r requirements.dev.txt` for development.

## Build executable

To compile as an executable, it requires:

- [PyInstaller](https://pypi.python.org/pypi/PyInstaller)

In order to create panhunt as a standalone executable run (works in both Linux and Windows):

However, you are advised  use a virtual environment. Update the path on the `build.sh` or `build.ps1` file and run. With the short scripts, you can clean the cache, include the original icon and the dependencies (works in both Linux and Windows). The example uses a virtual environment in a folder called `.venv`.

## Usage

```shell
usage: panhunt [-h] [-s SEARCH_DIR] [-f FILE_PATH] [-x EXCLUDE_DIRS] [-o REPORT_DIR] [-j JSON_DIR] [-u] [-C CONFIG] [-X EXCLUDE_PAN] [-q] [-v]

PAN Hunt v1.5: search directories and sub directories for documents containing PANs.

options:
  -h, --help       show this help message and exit
  -s SEARCH_DIR    base directory to search in (default: None)
  -f FILE_PATH     File path for single file scan (default: None)
  -x EXCLUDE_DIRS  directories to exclude from the search (use absolute paths) (default: None)
  -o REPORT_DIR    Report file directory for TXT formatted PAN report (default: ./)
  -j JSON_DIR      Report file directory for JSON formatted PAN report (default: None)
  -C CONFIG        configuration file to use (default: None)
  -X EXCLUDE_PAN   PAN to exclude from search (default: None)
  -q               No terminal output (default: False)
  -v               Verbose logging (default: False)
```

Simply running it with no arguments will search the `C:\` drive on Windows and filesystem under `/` on Linux, for documents containing PANs, and output to panhunt_<timestamp>.txt.

## Example Output

```yaml
FOUND PANs: D:\PANhunt\test\eml\test with attachments.eml (176.91KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\eml\test.eml (41.87KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\msg\test with attachments.msg (169.50KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\msg\test.msg (22.50KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\office\test.rtf (40.79KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\pdf\test.pdf (39.57KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\plain\test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\plain\dir2\test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test with attachments.eml\test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: success.tar\test.rtf (40.79KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.eml\None (36.77KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\gz\test.txt.gz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test with attachments.msg\test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: success.tar\test.rtf (40.79KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\office\test.docx\word/document.xml (3.50KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\office\test.pptx\ppt/slides/slide1.xml (1.68KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\office\test.xlsx\xl/sharedStrings.xml (328.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\tar\success.tar\dir2/test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\xz\test.txt.xz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\zip\test.zip\dir2/test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\zip\test.zip\test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt\test.docx\word/document.xml (3.50KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.docx\test.pptx\ppt/slides/slide1.xml (1.68KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.pptx\test.txt.gz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt.gz\test.txt.xz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt.xz\success.tar\dir2/test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.rtf\test.xlsx\xl/sharedStrings.xml (328.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt\test.docx\word/document.xml (3.50KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.docx\test.pptx\ppt/slides/slide1.xml (1.68KB)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.pptx\test.txt.gz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt.gz\test.txt.xz\test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.txt.xz\success.tar\dir2/test.txt (96.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: test.rtf\test.xlsx\xl/sharedStrings.xml (328.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\tar\success.tar.gz\success.tar\dir2/test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

FOUND PANs: D:\PANhunt\test\tar\success.tar.xz\success.tar\dir2/test.txt (54.00B)
        Mastercard:510510******5100
        Visa:401288******1881
        AMEX:371449*****8431

Report written to D:\PANhunt\out\panhunt_2024-09-14-221629.report
```

## Configuration

The script allows for a configuration to be written that will default the application with settings such that you don't need to
repeatedly specify exclude/include paths or the test PANs to exclude.

## Changelog

This for includes a full architectural change to allow extending the scanning capabilities by providing a new scanner. It is more modular and has more file searching capabilities. It means there is a performance impact for the sake of accuracy.

### v1.5

- Python version is now minimum 3.9
- The progress bars removed
- Each file within a container now considered a separate file
- Nested archive file handling problem fixed
- Removed unmask option
- Added `size limit` for files to large file search configurable
- Minimized memory footprint of PANs by removing them ASAP

### v1.4

- Removed file extension based filtering. Now it relies on `magic` results.

### v1.3

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

**NB!** There is at least 20% performance impact after refactoring. There are no performance improvements tried yet.
