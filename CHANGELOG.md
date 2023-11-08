# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
* limit text guessing by size

### Fixed
* bug with text guessing

## [0.1.1] - 2023-11-07

### Added
* optionally extract text info from record marker
* `--parsing` argument
* `--segments` argument
* `--include` argument

### Changed
* allow multiple filenames

### Fixed
* bug with `\\` markers
* include languages

## [0.1.0] - 2023-11-05

### Fixed
* no inflection **required**
* bug with lexicon-less extraction
* proper handling of conf dicts passed via python
* drop empty tables
* remove leading and trailing `-` from forms

### Added
* `dictionary` command

## [0.0.2] - 2023-07-02

### Added
* audio
* [cldf-ldd](https://fl.mt/cldf-ldd)
* better feedback
* more speed
* adding sources
* ex- or including text records
* replace characters in forms
* inflection

### Changed
* renamed to `unboxer`

### Fixed
* casting strings to path when using from a python script
* leaving out records without any data
* warning about duplicate records and removing them

## [0.0.1] - 2022-11-25

Initial release

[Unreleased]: https://github.com/fmatter/unboxer/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/fmatter/unboxer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fmatter/unboxer/compare/v0.0.2...v0.1.0
[0.0.2]: https://github.com/fmatter/unboxer/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/fmatter/unboxer/compare/v0.0.1...v0.0.1