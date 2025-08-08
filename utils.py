import os
import json
import re


def load_db_config(config_file: str = "db_conf.json") -> dict:
    """Load database configuration from JSON file with environment variable substitution."""
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Substitute environment variables in the format ${VAR_NAME}
    def substitute_env_vars(text: str) -> str:
        if isinstance(text, str):
            # Pattern to match ${VAR_NAME} or ${VAR_NAME:default_value}
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            def replacer(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""
                return os.environ.get(var_name, default_value)
            return re.sub(pattern, replacer, text)
        return text
    
    # Recursively substitute environment variables in the config
    def substitute_recursive(obj):
        if isinstance(obj, dict):
            return {key: substitute_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [substitute_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return substitute_env_vars(obj)
        else:
            return obj
    
    return substitute_recursive(config)
