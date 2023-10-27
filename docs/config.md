# Configuration
The unboxer's behavior can be modified by editing a [.yaml](https://yaml.org/spec/1.2.2/#chapter-2-language-overview) file and passing it to the `unbox` command:

```shell
unbox corpus <path/to/your/toolbox/texts.db> --conf <path/to/your/config.yaml>`.
```

A key-value pair added in your configuration file will override the default value.
Default values are stored in one of three built-in  files.
There is a [general configuration file](#interlinear_configyaml) for interlinear text, and specific files for [toolbox](#toolbox) and [shoebox](#shoebox).
These two files are identically structured and contain best-guess default values for the two applications.
By [default](site:usage), the toolbox configuration is loaded; shoebox can be specified with `--format shoebox`.

## General configuration
File: [`interlinear_config.yaml`](https://github.com/fmatter/unboxer/blob/main/src/unboxer/data/interlinear_config.yaml).

{!src/unboxer/data/interlinear_config.yaml!}

## Toolbox
File: [`toolbox.yaml`](https://github.com/fmatter/unboxer/blob/main/src/unboxer/data/toolbox.yaml).

{!src/unboxer/data/toolbox.yaml!}

## Shoebox
File: [`shoebox.yaml`](https://github.com/fmatter/unboxer/blob/main/src/unboxer/data/shoebox.yaml).

{!src/unboxer/data/shoebox.yaml!}
