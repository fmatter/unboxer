# unboxer

Extract data from shoebox and toolbox projects to CSV files.

![License](https://img.shields.io/github/license/fmatter/unboxer)
[![Tests](https://img.shields.io/github/actions/workflow/status/fmatter/unboxer/tests.yml?label=tests&branch=main)](https://github.com/fmatter/unboxer/actions/workflows/tests.yml)
[![Linting](https://img.shields.io/github/actions/workflow/status/fmatter/unboxer/lint.yml?label=linting&branch=main)](https://github.com/fmatter/unboxer/actions/workflows/lint.yml)
[![Codecov](https://img.shields.io/codecov/c/github/fmatter/unboxer)](https://app.codecov.io/gh/fmatter/unboxer/)
[![PyPI](https://img.shields.io/pypi/v/unboxer.svg)](https://pypi.org/project/unboxer)
![Versions](https://img.shields.io/pypi/pyversions/unboxer)

## Installation
```shell
pip install unboxer
```

## Usage
At the moment, there is only one command: `unbox corpus`, for collections of glossed texts.
To create a file `mytextdatabase.csv` from a toolbox file `mytextdatabase.txt`:

```shell
unbox corpus mytoolbox/mytextdatabase.txt
```

Project-specific configuration can be passed via `--conf your/config.yaml`; to see what options are available, check [the default configuration file](src/unboxer/data/interlinear_config.yaml) as well as the default configuration files for [toolbox](src/unboxer/data/toolbox.yaml) and [shoebox](src/unboxer/data/shoebox.yaml).

To create a [CLDF](cldf.clld.org/) version of the corpus, add the option `--cldf`.
For more help on how to run the command, use `unbox corpus --help`.

## Problems
1. if running `unbox` produces warnings, check your database for possible inconsistencies
2. if that did not solve your problem, [open an issue](https://github.com/fmatter/unboxer/issues/new)