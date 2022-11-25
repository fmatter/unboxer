# box2csv

Extract shoebox and toolbox data to CSV files.

![License](https://img.shields.io/github/license/fmatter/box2csv)

## Installation
`pip install box2csv`

## Usage
At the moment, there is only one command: `box2csv corpus`, for collections of glossed texts.
To create a file `mytextdatabase.csv` from a toolbox file `mytextdatabase.txt`:

```shell
box2csv corpus mytoolbox/mytextdatabase.txt
```

Project-specific configuration can be passed via `--conf your/config.yaml`; to see what options are available, check [the default configuration file](src/box2csv/data/config.yaml) as well as the default configuration files for [toolbox](src/box2csv/data/toolbox.yaml) and [shoebox](src/box2csv/data/shoebox.yaml).

To create a [CLDF](cldf.clld.org/) dataset, add the option `--cldf`.
For more help on how to run the command, use `box2csv corpus --help`.

## Problems
1. if running `box2csv` produces warnings, check your database for possible inconsistencies
2. if that did not solve your problem, [open an issue](https://github.com/fmatter/box2csv/issues/new)