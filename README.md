# PANhunt

[![Bandit](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/bandit.yml)
[![CodeQL](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/codeql.yml)
[![DevSkim](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml/badge.svg?branch=master)](https://github.com/zbalkan/PANhunt/actions/workflows/devskim.yml)

## Introduction

PANhunt is a tool that can be used to search drives for [primary account numbers (PANs)](https://www.pcisecuritystandards.org/glossary/#glossary-p:~:text=to%2DPoint%20Encryption.%E2%80%9D-,PAN,-Acronym%20for%20%E2%80%9Cprimary).

> PAN
>Acronym for “primary account number.” Unique payment card number (credit, debit, or prepaid cards, etc.) that identifies the issuer and the cardholder account.

The tool is useful for checking PCI DSS scope accuracy. Ensuring PAN does not leak out of the authorized locations and there's no clear text PAN within the infrastructure, the tool may help as a simple control.

## Acknowledgements

PANhunt remains rooted in the original [Dionach PANhunt project](https://github.com/dionach/PANhunt), created and released by Dionach Ltd. The original project made a simple, practical PAN discovery tool available to the PCI and security community, including the PST parsing foundation that this fork continues to build on.

This fork keeps the Dionach icon as a visible sign of respect for the original source, developer, and project history. The BSD-3-Clause license and copyright notice from Dionach Ltd. are preserved in this repository.

## Function

PANhunt uses regular expressions to look for Visa, MasterCard, AMEX and other credit card numbers across a broad set of document, mail, and archive formats. Archive and container formats are recursed so nested documents, emails, and attachments can be searched.

Currently supported searchable formats include:

- Plain text and text-like files, including CSV, XML, HTML, logs, source files, and flat OpenDocument XML (`.fodt`, `.fods`, `.fodp`) when detected as text
- Rich Text Format (`.rtf`)
- Legacy Microsoft Office binary files (`.doc`, `.xls`, `.ppt`)
- Modern Microsoft Office Open XML files (`.docx`, `.xlsx`, `.pptx`)
- OpenDocument containers (`.odt`, `.ott`, `.ods`, `.ots`, `.odp`, `.otp`, `.odg`, `.otg`, `.odf`, `.odm`)
- PDF documents (`.pdf`)
- Outlook and email stores/messages (`.pst`, `.msg`, `.eml`, `.mbox`), including supported attachments
- Recursive archives and compressed files (`.zip`, `.tar`, `.gz`, `.xz`), including Office and OpenDocument container files

PANhunt will list but does not yet search Access databases.

## Architecture

PANhunt follows a layered, dependency-injected architecture:

- **`PanHuntService`** — orchestrates a full scan session with no UI concerns
- **`CliPresenter`** — handles all terminal output and report file writing
- **`Hunter`** / **`Dispatcher`** — file-system traversal and concurrent scanning
- **`ScannerFactory`** / **`ArchiveFactory`** — produce scanner and archive-handler instances for each file type; custom scanners can be registered at runtime
- **`ScanConfiguration`** — immutable configuration object created once and injected into all components
- **`ScanResult`** / **`Finding`** — data-transfer objects carrying structured output

The service and presenter layers are fully decoupled, making it straightforward to embed PANhunt in a larger application or swap the CLI presenter for a different UI.

## Installation and publishing

PANhunt requires Python 3.9 or later. For normal usage, install the package and run the console script:

```shell
pipx install panhunt
panhunt --help
```

### libmagic prerequisite on non-Windows systems

PANhunt uses `python-magic` for file type detection. On Windows, the packaged `python-magic-bin` dependency provides the native library. On Linux and macOS, `python-magic` usually requires the OS-level `libmagic` library to be installed before PANhunt can import and scan files successfully. Install it with your platform package manager before or after installing PANhunt, for example:

```shell
# Debian / Ubuntu
sudo apt-get install libmagic1

# Fedora
sudo dnf install file-libs

# macOS with Homebrew
brew install libmagic
```

For local development, install the project with its development extras from the repository root:

```shell
pip install -e .[dev]
pytest
```

## Testing

The test suite uses `pytest` and covers the core scanning logic, configuration, factories, service layer, and presenter.

```shell
pytest src/tests/
```

To include coverage details, run `pytest --cov=panhunt src/tests/`.

## Usage

```shell
usage: panhunt [-h] [-x EXCLUDE_DIRS] [-o REPORT_DIR] [-j JSON_DIR] [-C CONFIG] [-X EXCLUDE_PAN] [-w WORKERS] [-q] [target_path]

PANHunt : search directories and sub directories for documents containing PANs.

positional arguments:
  target_path      file or directory to search (default: None)

options:
  -h, --help       show this help message and exit
  -x EXCLUDE_DIRS  directories to exclude from the search (use absolute paths) (default: None)
  -o REPORT_DIR    Report file directory for TXT formatted PAN report (default: ./)
  -j JSON_DIR      Report file directory for JSON formatted PAN report (default: None)
  -C CONFIG        configuration file to use (default: None)
  -X EXCLUDE_PAN   PAN to exclude from search (default: None)
  -w WORKERS       Number of worker threads (default: 1) (default: None)
  -q               No terminal output (default: False)

For advanced scanning controls, use -C config.ini. The configuration file supports additional options beyond the command-line parameters.
```

Running PANhunt without a target path or `-C config.ini` no longer starts a root-directory scan. It prints a short reminder to use `-h` or `--help` and exits without scanning. Reports are written as `panhunt_<timestamp>.report` in the report directory, and JSON reports are written as `panhunt_<timestamp>.json` when `-j` or the `json` configuration key is set.

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

The script allows for a configuration file that sets default values, so you don't need to repeatedly specify paths or PANs to exclude on the command line.

Example `config.ini`:

```ini
[DEFAULT]
# Target can be supplied as target, search, or file.
search = /data
exclude = /data/logs,/data/tmp
outfile = /var/reports
json = /var/reports
excludepans = 4111111111111111
sizeLimit = 21474836480
# Omit workers to default to the host CPU core count; set it to override.
workers = 2
quiet = false

# Optional safety/resource limits. Values are bytes unless otherwise noted.
maxScanDepth = 25
maxChildJobs = 100000
maxTotalExpandedBytes = 21474836480
maxArchiveMembers = 10000
maxArchiveCompressionRatio = 100
maxArchivePathLength = 4096
archiveSpoolThreshold = 8388608
maxAttachmentSize = 21474836480
maxAttachmentsPerMessage = 1000
maxTotalAttachmentBytes = 21474836480
allowedArchiveTypes =
deniedArchiveTypes =
parserTimeoutSeconds = 30
parserMemoryLimitBytes = 536870912
maxPdfPages = 100
maxPdfTextBytes = 10485760
```

Pass the config file with `-C config.ini`. The configuration file is the preferred way to use advanced scanning controls because it supports more options than the command-line parameters, including safety limits for nested archives, compressed data, attachments, parser isolation, and PDF extraction. Command-line quiet mode (`-q`) overrides the `quiet` value from the configuration file. The default `sizeLimit` is 8 GB, and the default worker count is the host CPU core count. Set `sizeLimit` in an INI file when a scheduled scan needs a larger limit, such as the 20 GB systemd examples below. The `sizeLimit` setting also updates the default total expanded-byte and attachment-byte limits unless those more specific settings are supplied.


## Systemd timer example

Example system-level systemd files are available in `examples/systemd/`. They run PANhunt against `/opt` and `/var/log`, skip `/var/log/sudo-io`, `/var/log/lastlog`, and the report directory itself, allow files up to 20 GB, omit an explicit worker count so PANhunt uses the CPU core count, write JSON reports under `/var/log/panhunt` for SIEM collection, and cap service CPU usage with `CPUQuota=60%`. Copy the `.ini` files to `/etc/panhunt/`, replace `PANHUNT_BIN` in the service with the absolute path returned by `which panhunt`, copy the service/timer files to `/etc/systemd/system/`, and enable the timer with `systemctl enable --now panhunt.timer`.

## Restricting memory usage

An important detail is that when working with large compressed files such as compressed log files larger than memory, panhunt may use all the CPU power, and it may be better to limit the CPU usage to prevent issues. If you are using `systemd`, a command like `systemd-run --scope -p CPUQuota=60% panhunt <your parameters here>` would save your resources.
