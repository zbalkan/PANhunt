# Changelog

All notable changes to this project are documented in this file.

PANhunt follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-17

### Added

- Added a layered scanning architecture with `PanHuntService`, `CliPresenter`, `ScanConfiguration`, `ScanResult`, scanner factories, and archive factories to separate configuration, orchestration, reporting, and file-format handling.
- Added a thread-safe `InMemoryJobBuffer` and bounded worker-pool dispatcher with configurable worker counts for safer producer/consumer scanning.
- Added scan context resource budgets for nested content, archives, attachments, and PDF parsing to limit expansion and parsing risk.
- Added OpenDocument archive scanning support.
- Added console scan progress when quiet mode is disabled.
- Added scan configuration validation and refreshed sample configuration defaults.
- Added Python packaging through `pyproject.toml`, wheel publishing scripts, pinned runtime/development requirements, and CI workflow coverage.
- Added an expanded automated test suite covering scanners, archives, dispatching, reports, configuration, and integration behavior.

### Changed

- Replaced the `PANHuntConfiguration` singleton with explicit `ScanConfiguration` objects and central constants.
- Refactored report generation, CLI argument handling, scanner payload narrowing, archive stream handling, and temporary-file usage for clearer behavior across platforms.
- Changed default scan size limits to 8 GB after memory handling improvements.
- Updated PAN detection patterns and dependency constraints.
- Replaced PyInstaller build scripts with wheel publication scripts.
- Improved friendly file-size formatting and stream payload size reporting.
- Updated README documentation for the new architecture, usage, packaging, and behavior.

### Removed

- Removed redundant garbage-collection calls, unused dispatcher memory-check code, redundant CLI type conversions, and obsolete counters/logging paths.

### Fixed

- Fixed PAN discovery so all matching PANs are reported instead of only the first match per card brand.
- Fixed excluded PAN handling and Windows directory exclusion path case-sensitivity.
- Fixed recursive file enumeration, current-directory handling, and file-like ZIP typing.
- Fixed invalid ZIP containers, legacy Office binary scanning, PST parsing, MSG/EML handling, and gzip header filename handling.
- Fixed PDF parsing robustness by isolating parsing in subprocesses with resource limits and correcting PDF type handling.
- Fixed archive stream portability, nested archive scanning, large compressed-file streaming, and stream-backed finding sizes.
- Fixed quiet mode, Ctrl+C/keyboard-interrupt handling, console traceback suppression, scan status indentation, and warning/report headers.
- Fixed Python 3.9 compatibility, typing issues, mimetype fallback initialization, cross-platform signal alarm access, and private `genericpath.exists()` usage.
- Fixed `PANHuntException` inheritance so it correctly extends `Exception`.

## [1.6] - 2024-12-10

### Added

- Started using a separate changelog IAW [keepachangelog.com](https://keepachangelog.com/en/1.1.0/)

### Fixed

- Gz extraction fails on Linux (#80)

### Changed

- Upgraded dependencies

## [1.5] - 2024-09-03

### Added

- Added a configurable size limit for large-file searches.

### Changed

- Increased the minimum Python version to 3.9.
- Treated each file inside a container as a separate file.
- Minimized the memory footprint of PANs by removing them as soon as possible.

### Removed

- Removed progress bars.
- Removed the unmask option.
- Removed the verbose flag.

### Fixed

- Fixed nested archive handling.

## [1.4] - 2023-09-16

### Changed

- Removed file extension based filtering. PANhunt now relies on `magic` results.

## [1.3] - 2023-09-15

### Added

- Added Python 3 support.
- Added file type detection via `python-magic` instead of depending only on file extensions.
- Added default text logging for accountability.
- Added optional JSON report generation for third-party integrations.
- Added the `-q`/`--quiet` flag to disable terminal output for integrations.
- Added the `-f`/`--filepath` flag to enable single-file scans.
- Added `.eml` and `.mbox` scanning support.
- Added PDF scanning support, with OCR still not working as expected.

### Changed

- Changed text report output to accept only a directory argument while using the fixed filename template `panhunt_<timestamp>.report`.
- Changed JSON report output to use the filename template `panhunt_<timestamp>.json`.
- Noted an expected performance impact of at least 20% after the refactor, with performance optimization still pending.
