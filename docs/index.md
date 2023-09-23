# unboxer

There are three CLI commands available, called with `unboxer COMMAND`:

* [corpus](#corpus)
* [dictionary](#dictionary)
* [wordlist](#wordlist)

::: mkdocs-click
    :module: unboxer.cli
    :command: corpus


::: mkdocs-click
    :module: unboxer.cli
    :command: dictionary

::: mkdocs-click
    :module: unboxer.cli
    :command: wordlist

Project-specific configuration can be passed via `--conf your/config.yaml`; to see what options are available, check [the default configuration file](src/unboxer/data/interlinear_config.yaml) as well as the default configuration files for [toolbox](src/unboxer/data/toolbox.yaml) and [shoebox](src/unboxer/data/shoebox.yaml).

## Problems
1. if running `unbox` produces warnings, check your database for possible inconsistencies
2. if that did not solve your problem, [open an issue](https://github.com/fmatter/unboxer/issues/new)