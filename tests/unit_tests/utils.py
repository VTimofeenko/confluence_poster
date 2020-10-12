import toml


def mk_tmp_file(tmp_path, filename: str = None,
                config_to_clone: str = 'config.toml',
                key_to_pop: str = None,  # key path in form 'first_key.second_key' to descend into config
                key_to_update: str = None, value_to_update=None):
    # Helper function to break config file in various ways
    if [key_to_update, value_to_update].count(None) == 1:
        raise ValueError("Only one update-related parameter was supplied")

    if filename is None:
        config_file = tmp_path / tmp_path.name
    else:
        config_file = tmp_path / filename
    original_config = toml.load(config_to_clone)
    if key_to_pop:
        _ = original_config
        li = key_to_pop.split('.')
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.pop(key)
    if key_to_update:
        _ = original_config
        li = key_to_update.split('.')
        for key in li:
            if key != li[-1]:
                _ = _[key]
            else:
                _.update({key: value_to_update})
    config_file.write_text(toml.dumps(original_config))
    return config_file
