"""Top-level package for box2csv."""
import logging
import re
from pathlib import Path
import colorlog
import pandas as pd
from slugify import slugify
from box2csv.cldf import create_cldf


handler = colorlog.StreamHandler(None)
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)-7s%(reset)s %(message)s")
)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.propagate = True
log.addHandler(handler)


__author__ = "Florian Matter"
__email__ = "fmatter@mailbox.org"
__version__ = "0.0.2.dev"

used_slugs = [""]


def _slugify(text):
    first = slugify(text)
    if first not in used_slugs:
        return first
    i = 0
    slug_cand = f"{first}-{i}"
    while slug_cand in used_slugs:
        i += 1
        slug_cand = f"{first}-{i}"
    return slug_cand


def _remove_spaces(text):
    for sep in ["- ", " -"]:
        while sep in text:
            text = text.replace(sep, sep.strip())
    return re.sub(r"\s+", "\t", text)


def _get_fields(record, rec_marker):
    out = {}
    marker = None
    for line in record.split("\n"):
        if not line.startswith("\\"):
            out[marker] += " " + line
        elif " " in line:
            marker, content = line.split(" ", 1)
            if marker in out:
                out[marker] += " " + content
            else:
                out[marker] = content
        else:
            out[line] = ""
    if "".join([v for k, v in out.items() if k != rec_marker]) == "":
        return None
    return out


def _fix_clitics(string):
    string = string.replace("=\t", "=").replace("\t=", "=")
    return string


def _fix_glosses(rec, goal="Analyzed_Word", target="Gloss", sep="\t"):
    if rec[goal].count(sep) != rec[target].count(sep):
        rec[target] = rec[target].strip(sep)
        if rec[goal].count(sep) != rec[target].count(sep):
            rec[goal] = rec[goal].strip(sep)
    return rec


def extract_corpus(database_file, conf, output_dir=".", cldf=False):
    """Extract text records from a corpus.

    Args:
        database_file (str): The path to the corpus database file.
        conf (dict): Configuration (see) todo: insert link
        cldf (bool, optional): Should a CLDF dataset be created? Defaults to `False`.
    """
    database_file = Path(database_file)
    record_marker = "\\"+conf["record_marker"]
    with open(database_file, "r", encoding=conf["encoding"]) as f:
        content = f.read()
    records = content.split(record_marker)
    out = []
    for record in records[1::]:
        res = _get_fields(record_marker + record, record_marker)
        if res:
            out.append(res)
        else:
            log.warning("Empty record:")
            log.warning(record)
    df = pd.DataFrame.from_dict(out)
    if not df[record_marker].is_unique:
        log.warning("Found duplicate IDs, will only keep first of each:")
        dupes = df[df.duplicated(record_marker)]
        print(dupes)
        df.drop_duplicates(record_marker, inplace=True)
    df.rename(columns=conf["mappings"], inplace=True)
    if "ID" in df:
        if conf["slugify"]:
            df["ID"] = df["ID"].map(_slugify)
    else:
        df["ID"] = df.index
    df.fillna("", inplace=True)
    for col in df.columns:
        if col in conf["aligned_fields"]:
            df[col] = df[col].apply(_remove_spaces)
    df = df.apply(_fix_glosses, axis=1)
    # df = df.apply(_fix_glosses, axis=1) # this may be needed somehow?
    if conf["fix_clitics"]:
        for col in conf["aligned_fields"]:
            df[col] = df[col].apply(_fix_clitics)
    if "Primary_Text" in df.columns:
        df["Primary_Text"] = df["Primary_Text"].apply(lambda x: re.sub(r"\s+", " ", x))
    if output_dir:
        df.to_csv(
            (Path(output_dir) / database_file.name).with_suffix(".csv"), index=False
        )
    if cldf:
        create_cldf(tables={"ExampleTable": df}, conf=conf, output_dir=output_dir)
    return df
