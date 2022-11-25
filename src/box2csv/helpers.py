import yaml
from importlib_resources import files

DATA = files("box2csv") / "data"

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        dic = yaml.load(f, Loader=yaml.SafeLoader)
        if "mappings" in dic:
            if "record_marker" in dic:
                dic["mappings"][dic["record_marker"]] = "ID"
            for marker in list(dic["mappings"].keys()):
                dic["mappings"]["\\" + marker] = dic["mappings"].pop(marker)
        return dic


def load_default_config(filename):
    config = load_yaml(DATA / "config.yaml")
    config.update(load_yaml(DATA / f"{filename}.yaml"))
    return config


def load_config(path, default="toolbox"):
    config = load_default_config(default)
    config.update(load_custom_config(path))
    return config


def load_custom_config(config_path):
    if (config_path).is_file():
        return load_yaml(config_path)
    return {}
