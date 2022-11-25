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

You can pass `--format shoebox` for shoebox projects.
`--cldf` will create a CLDF dataset.
Additional configuration can be passed via `--conf your/config.yaml`; available options can be seen in the default configurations for [toolbox](src/box2csv/data/toolbox.yaml) and [shoebox](src/box2csv/data/shoebox.yaml).