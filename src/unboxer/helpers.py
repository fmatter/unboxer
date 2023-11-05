from pathlib import Path

import yaml
from importlib_resources import files
from slugify import slugify

DATA = files("unboxer") / "data"


def fix_glosses(rec, goal="Analyzed_Word", target="Gloss", sep="\t"):
    if rec[goal].count(sep) != rec[target].count(sep):
        rec[target] = rec[target].strip(sep)
        if rec[goal].count(sep) != rec[target].count(sep):
            rec[goal] = rec[goal].strip(sep)
    return rec


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        dic = yaml.load(f, Loader=yaml.SafeLoader)
        return dic


def markerize(config):
    for mapping_str, id_field in [
        ("interlinear_mappings", "record_marker"),
        ("lexicon_mappings", "entry_marker"),
    ]:
        if id_field in config and id_field == "record_marker":
            config.setdefault(mapping_str, {})
            config[mapping_str][config[id_field]] = "ID"
        if mapping_str in config:
            for marker in list(config[mapping_str].keys()):
                if "\\" not in marker:
                    new_marker = "\\" + marker
                else:
                    new_marker = marker
                config[mapping_str][new_marker] = config[mapping_str].pop(marker)
    for single in ["parsing_surface", "parsing_underlying"]:
        if single in config:
            config[single] = "\\" + config[single]
    return config


def load_default_config(filename):
    config = load_yaml(DATA / "interlinear_config.yaml")
    config.update(markerize(load_yaml(DATA / f"{filename}.yaml")))
    return config


def load_config(path, default="toolbox"):
    config = load_default_config(default)
    config.update(load_custom_config(path))
    return config


def load_custom_config(config_path):
    if not config_path:
        return {}
    config_path = Path(config_path)
    if (config_path).is_file():
        return markerize(load_yaml(config_path))
    return {}


used_slugs = {}
slug_dict = {}


def _slugify(text, marker, ids=True):
    used_slugs.setdefault(marker, [])
    slug_dict.setdefault(marker, {})
    if not ids and text in slug_dict[marker]:
        return slug_dict[marker][text]
    first = slugify(text)
    if first == "":
        first = "null"
    if first not in used_slugs[marker]:
        used_slugs[marker].append(first)
        slug_dict[marker][text] = first
        return first
    i = 0
    slug_cand = f"{first}-{i}"
    while slug_cand in used_slugs[marker]:
        i += 1
        slug_cand = f"{first}-{i}"
    used_slugs[marker].append(slug_cand)
    slug_dict[marker][text] = slug_cand
    return slug_cand
