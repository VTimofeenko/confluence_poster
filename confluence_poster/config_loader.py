from confluence_poster.poster_config import Config, PartialConfig
from collections import UserDict
from collections.abc import Mapping
from pathlib import Path


def merge_configs(first_config: Mapping, other_config: Mapping):
    """Merges two configs together, like so:
    {'auth': {'user': 'a'}} + {'auth': {'password': 'b'}} = {'auth': {'user': 'a', 'password': 'b'}}.
    Other config values overwrite values in first config."""
    for key in set(first_config).union(other_config):
        if key in first_config and key in other_config:
            check_list = [
                isinstance(_, dict) for _ in [first_config[key], other_config[key]]
            ]
            if all(check_list):
                yield key, dict(merge_configs(first_config[key], other_config[key]))
            elif isinstance(first_config[key], type(other_config[key])):
                yield key, other_config[key]
            elif check_list.count(True) == 1:  # one and only one is a dict
                raise ValueError(
                    f"{key} is a section in one of the configs, not in another"
                )
            else:
                raise ValueError(f"{key} key is malformed in one of the configs")

        elif key in first_config:
            yield key, first_config[key]
        else:
            yield key, other_config[key]


def load_config(local_config: Path) -> Config:
    """Function that goes through the config directories trying to load the config.
    Reads configs from XDG_CONFIG_DIRS, then from XDG_CONFIG_HOME, then the local one - either the default one, or
    supplied through command line."""
    import xdg.BaseDirectory
    from importlib import reload

    reload(xdg.BaseDirectory)

    final_config = UserDict()
    for path in list(xdg.BaseDirectory.load_config_paths("confluence_poster"))[::-1]:
        config_path = Path(path) / "config.toml"
        if config_path.exists():
            final_config = dict(
                merge_configs(final_config, PartialConfig(file=config_path))
            )

    final_config = dict(merge_configs(final_config, PartialConfig(file=local_config)))

    return Config(data=final_config)
