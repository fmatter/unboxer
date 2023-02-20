"""Top-level package for unboxer."""
import logging
import re
import sys
from pathlib import Path
import colorlog
import pandas as pd
from humidifier import get_values
from humidifier import humidify
from morphinder import Morphinder
from unboxer.cldf import create_cldf
from unboxer.cldf import create_wordlist_cldf
from unboxer.cldf import get_data


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


def _remove_spaces(text):
    for sep in ["- ", " -"]:
        while sep in text:
            text = text.replace(sep, sep.strip())
    return re.sub(r"\s+", "\t", text)


def id_glosses(gloss, sep=None):
    res = [humidify(g, key="glosses") for g in re.split(r"\.\b", gloss)]
    if sep:
        return sep.join(res)
    return res


def _get_fields(record, rec_marker, multiple, sep):
    out = {}
    marker = None
    for line in record.split("\n"):
        if line == "":
            continue
        if not line.startswith("\\"):
            out[marker] += " " + line
        elif " " in line:
            marker, content = line.split(" ", 1)
            if marker in out:
                if marker not in multiple:
                    out[marker] += " " + content
                else:
                    out[marker] += sep + content
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


def extract_morphs(lexicon, sep):
    morphs = []
    morphemes = []
    for rec in lexicon.to_dict("records"):
        m_id = rec["ID"]
        dic = {
            "Meaning": rec["Meaning"],
            "Part_Of_Speech": rec["Part_Of_Speech"],
            "Morpheme_ID": m_id,
        }
        morphs.append({**{"Form": rec["Headword"], "ID": rec["ID"]}, **dic})
        if "Variants" in rec and rec["Variants"] != "":
            for c, x in enumerate(rec["Variants"].split(sep)):
                morphs.append({**{"Form": x, "ID": f"{m_id}-{c}"}, **dic})
        morphemes.append(rec)
    return pd.DataFrame.from_dict(morphemes), pd.DataFrame.from_dict(morphs)


def build_slices(df, morphinder=None, obj_key="Analyzed_Word", gloss_key="Gloss"):
    df = df.copy()
    for c in [obj_key, gloss_key]:
        df[c] = df[c].apply(lambda x: re.sub(r"-\s+", "-INTERN", x))
        df[c] = df[c].apply(lambda x: re.sub(r"\s+-", "INTERN-", x))
        df[c] = df[c].apply(lambda x: re.split(r"\s+", x))
    wfs = {}
    w_slices = []
    s_slices = []
    w_meanings = {}
    for sentence in df.to_dict("records"):
        for s_idx, (obj, gloss) in enumerate(
            zip(sentence[obj_key], sentence[gloss_key])
        ):
            w_obj = obj.replace("INTERN", "")
            w_gloss = gloss.replace("INTERN", "")
            w_id = humidify(f"{w_obj}-{w_gloss}", "wordforms")
            meaning_id = humidify(w_gloss, "meanings")
            if meaning_id not in w_meanings:
                w_meanings[meaning_id] = {"ID": meaning_id, "Name": w_gloss}
            if w_id == "":
                log.warning("EMPTY")
                continue
            if w_id not in wfs:
                if w_gloss != "":
                    wfs[w_id] = {
                        "ID": w_id,
                        "Form": w_obj.replace("-", ""),
                        "Gloss": w_gloss,
                        "Parameter_ID": humidify(w_gloss, "meanings"),
                        "Morpho_Segments": w_obj.split("-"),
                    }
                if morphinder:
                    for m_idx, (morph_obj, morph_gloss) in enumerate(
                        zip(obj.split("INTERN"), gloss.split("INTERN"))
                    ):
                        if (
                            morph_obj is None
                            or morph_gloss is None
                            or morph_gloss == "***"
                        ):
                            continue
                        morph_gloss = morph_gloss.strip("-").strip("=")
                        m_id, sense = morphinder.retrieve_morph_id(
                            morph_obj,
                            morph_gloss,
                            "",
                            gloss_key="Meaning",
                            type_key="Part_Of_Speech",
                        )
                        if m_id:
                            w_slices.append(
                                {
                                    "ID": f"{w_id}-{m_id}",
                                    "Wordform_ID": w_id,
                                    "Morph_ID": m_id,
                                    "Form_Meaning": meaning_id,
                                    "Gloss": morph_gloss,
                                    "Morpheme_Meaning": humidify(
                                        morph_gloss, "gloss_meanings"
                                    ),
                                    "Form": morph_obj,
                                    "Index": m_idx,
                                }
                            )
            s_slices.append(
                {
                    "ID": f"{sentence['ID']}{s_idx}",
                    "Example_ID": sentence["ID"],
                    "Wordform_ID": w_id,
                    "Form": w_obj.replace("-", ""),
                    "Segmentation": w_obj,
                    "Gloss": w_gloss,
                    "Parameter_ID": meaning_id,
                    "Index": s_idx,
                }
            )
    if not morphinder:
        w_slices = None
    else:
        w_slices = pd.DataFrame.from_dict(w_slices)
    return (
        pd.DataFrame.from_dict(wfs.values()),
        pd.DataFrame.from_dict(w_meanings.values()),
        pd.DataFrame.from_dict(s_slices),
        w_slices,
    )


def extract_corpus(database_file, conf, lexicon=None, output_dir=".", cldf=False):
    """Extract text records from a corpus.

    Args:
        database_file (str): The path to the corpus database file.
        conf (dict): Configuration (see) todo: insert link
        cldf (bool, optional): Should a CLDF dataset be created? Defaults to `False`.
    """
    database_file = Path(database_file)
    record_marker = "\\" + conf["record_marker"]
    sep = conf["cell_separator"]

    try:
        with open(database_file, "r", encoding=conf["encoding"]) as f:
            content = f.read()
    except UnicodeDecodeError:
        log.error(
            f"""Could not open the file with the encoding [{conf["encoding"]}].
Make sure that you are not parsing a shoebox project as toolbox or vice versa.
You can also explicitly set the correct file encoding in your config."""
        )
        sys.exit()
    records = content.split(record_marker)
    out = []
    for record in records[1::]:
        res = _get_fields(record_marker + record, record_marker, multiple=[], sep=sep)
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
    df.rename(columns=conf["interlinear_mappings"], inplace=True)
    if "Analyzed_Word" not in df.columns:
        raise ValueError("Did not find Analyzed_Word:", conf["interlinear_mappings"])
    if "ID" in df:
        if conf["slugify"]:
            df["ID"] = df["ID"].apply(lambda x: humidify(x, "sentence_id", unique=True))
    else:
        df["ID"] = df.index
    df.fillna("", inplace=True)

    if lexicon:
        lex_df = extract_lexicon(lexicon, conf=conf)
        morphemes, morphs = extract_morphs(lex_df, sep)
        morphinder = Morphinder(morphs)
    else:
        tdf = df.copy()
        morphs = {}
        for c in ["Analyzed_Word", "Gloss"]:
            tdf[c] = df[c].apply(lambda x: re.sub(r"-\s+", "-INTERN", x))
            tdf[c] = df[c].apply(lambda x: re.sub(r"\s+-", "INTERN-", x))
            tdf[c] = df[c].apply(lambda x: re.split(r"\s+", x))
        for i, rec in tdf.iterrows():
            for obj, gloss in zip(rec["Analyzed_Word"], rec["Gloss"]):
                morph_id = humidify(obj + "-" + gloss, key="pairs")
                if morph_id not in morphs:
                    morphs[morph_id] = {
                        "ID": morph_id,
                        "Form": obj,
                        "Meaning": gloss.strip("-").strip("="),
                    }
        morphs = pd.DataFrame.from_dict(morphs.values())
        morphinder = Morphinder(morphs)
    wordforms, form_meanings, sentence_slices, morph_slices = build_slices(
        df, morphinder
    )
    morph_meanings = {
        string: {"ID": humidify(string, key="meanings"), "Name": string}
        for string in set(morphs["Meaning"])
    }
    for col in df.columns:
        if col in conf["aligned_fields"]:
            df[col] = df[col].apply(_remove_spaces)
    df = df.apply(_fix_glosses, axis=1)
    if conf["fix_clitics"]:
        for col in conf["aligned_fields"]:
            df[col] = df[col].apply(_fix_clitics)
    if "Primary_Text" in df.columns:
        df["Primary_Text"] = df["Primary_Text"].apply(lambda x: re.sub(r"\s+", " ", x))

    wordforms["Language_ID"] = conf.get("Language_ID", "undefined")
    wordforms = wordforms[wordforms["Form"] != ""]

    if lexicon:
        morphemes["Language_ID"] = conf.get("Language_ID", "undefined")
    morphs["Language_ID"] = conf.get("Language_ID", "undefined")
    if not morphs["ID"].is_unique:
        log.warning("Duplicate IDs in morph table, only keeping first instances:")
        log.warning(morphs[morphs.duplicated(subset="ID", keep=False)])
        morphs.drop_duplicates(subset="ID", inplace=True)

    if output_dir:

        df.to_csv(
            (Path(output_dir) / database_file.name).with_suffix(".csv"), index=False
        )
        morphs.to_csv((Path(output_dir) / "morphs.csv"), index=False)
        if lexicon:
            morphemes.to_csv((Path(output_dir) / "morphemes.csv"), index=False)
    if cldf:
        tables = {"ExampleTable": df}
        tables[
            "exampleparts"
        ] = sentence_slices  # .rename(columns={"Gloss": "Parameter_ID"})
        if lexicon:
            morphemes["Name"] = morphemes["Headword"]
            morphemes["Parameter_ID"] = morphemes["Meaning"].apply(
                lambda x: morph_meanings[x]["ID"]
            )

        morphs["Name"] = morphs["Form"]
        morph_slices["Gloss_ID"] = morph_slices["Gloss"].apply(id_glosses)
        tables["glosses"] = pd.DataFrame.from_dict(
            [{"ID": v, "Name": k} for k, v in get_values("glosses").items()]
        )
        morphs["Parameter_ID"] = morphs["Meaning"].apply(
            lambda x: morph_meanings[x]["ID"]
        )
        tables["wordforms"] = wordforms
        morph_meanings = pd.DataFrame.from_dict(
            [
                x
                for x in morph_meanings.values()
                if x["ID"] not in list(form_meanings["ID"])
            ]
        )
        tables["ParameterTable"] = pd.concat([form_meanings, morph_meanings])
        sentence_slices["Form_Meaning"] = sentence_slices["Gloss"]
        tables["morphs"] = morphs
        tables["wordformparts"] = morph_slices
        if lexicon:
            lexicon, meanings = get_data(lex_df)
            tables["morphemes"] = morphemes
            tables["ParameterTable"] = pd.concat([meanings, form_meanings])
            tables["ParameterTable"].drop_duplicates(subset="ID", inplace=True)
        create_cldf(tables=tables, conf=conf, output_dir=output_dir)
    return df


def extract_lexicon(database_file, conf, output_dir=".", cldf=False):
    database_file = Path(database_file)
    entry_marker = "\\" + conf["entry_marker"]
    with open(database_file, "r", encoding=conf["encoding"]) as f:
        content = f.read()
    if entry_marker not in content:
        raise ValueError(
            f"record_marker is defined as '{entry_marker}', which is not found in the database."
        )
    records = content.split(entry_marker)
    out = []
    sep = conf["cell_separator"]
    for record in records[1::]:
        res = _get_fields(entry_marker + record, entry_marker, ["\a"], sep=sep)
        if res:
            out.append(res)
        else:
            log.warning("Empty record:")
            log.warning(record)
    df = pd.DataFrame.from_dict(out)
    df.rename(columns=conf["lexicon_mappings"], inplace=True)
    df.fillna("", inplace=True)
    df["ID"] = df.apply(
        lambda x: humidify(f"{x['Headword']}-{x['Meaning']}", "form", unique=True),
        axis=1,
    )

    morphemes, morphs = extract_morphs(df, sep)

    if output_dir:
        df.to_csv(
            (Path(output_dir) / database_file.name).with_suffix(".csv"), index=False
        )

    if cldf:
        create_wordlist_cldf(df, conf=conf, output_dir=output_dir)
    return df
