# box2csv

Extract shoebox and toolbox data to CSV files.

![License](https://img.shields.io/github/license/fmatter/box2csv)

## Installation
`pip install box2csv`

## Usage
At the moment, there is only one command: `box2csv corpus`, for collections of glossed texts.
To create a file `texts.csv` from a toolbox file `texts.txt`:

```shell
box2csv corpus mytoolbox/texts.txt
```

Project-specific configuration can be passed via `--conf your/config.yaml`; available options can be seen in [the default configuration file](src/box2csv/data/config.yaml) as well as those specific for [toolbox](src/box2csv/data/toolbox.yaml) and [shoebox](src/box2csv/data/shoebox.yaml).

For more help on how to run the command, use `box2csv corpus --help`.

## Problems
1. if running `box2csv` produces warnings, check your database for possible inconsistencies
2. if that did not solve your problem, [open an issue](https://github.com/fmatter/box2csv/issues/new)