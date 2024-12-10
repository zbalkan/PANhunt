# Changelog

## [1.6] - 2024-12-10

### Added

- Started using a separate changelog IAW [keepachangelog.com](https://keepachangelog.com/en/1.1.0/)

### Fixed

- Gz extraction fails on Linux (#80)

### Changed

- Upgraded dependencies

## [1.5] - 2024-09-03

- Python version is now minimum 3.9
- The progress bars removed
- Each file within a container now considered a separate file
- Nested archive file handling problem fixed
- Removed unmask option
- Added `size limit` for files to large file search configurable
- Minimized memory footprint of PANs by removing them ASAP
- Removed verbose flag

## [1.4] - 2023-09-16

- Removed file extension based filtering. Now it relies on `magic` results.

## [1.3] - 2023-09-15

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
