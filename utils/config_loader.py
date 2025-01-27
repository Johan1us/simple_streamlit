import os
import json

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
print(f"CONFIG_DIR = {CONFIG_DIR}")


class ConfigLoader:
    def __init__(self, config_dir: str = CONFIG_DIR):
        self.config_dir = config_dir

    def load_config(self, dataset_name: str) -> dict:
        # Normaliseer de datasetnaam tot bestandsnaam.
        # Je zou bijvoorbeeld kunnen aannemen dat de datasetnaam spaties kan bevatten.
        # Als er een direct mapping is, kun je ook een dict aanhouden die datasetnaam op filename mappt.
        # Voor nu gaan we er even vanuit dat dataset_name bijvoorbeeld "po_daken" heet en in "po_daken.json" staat.

        filename = f"{dataset_name.lower().replace(' ', '_')}.json"
        path = os.path.join(self.config_dir, filename)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found for dataset '{dataset_name}' at {path}")

        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Eventuele validatie
        required_keys = ["dataset", "objectType", "attributes"]
        for rk in required_keys:
            if rk not in config:
                raise ValueError(f"Missing required key '{rk}' in config for dataset {dataset_name}")

        if not isinstance(config["attributes"], list):
            raise ValueError(f"'attributes' should be a list in config for dataset {dataset_name}")

        return config

if __name__ == '__main__':
    loader = ConfigLoader()
    config = loader.load_config("po_daken")
    print(config)
