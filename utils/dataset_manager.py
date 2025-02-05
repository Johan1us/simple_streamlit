import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import streamlit as st

from utils.api_client import APIClient

logging.basicConfig(level=logging.DEBUG)

def initialize_config_folder(project_root: str) -> Path:
    """
    Resolve the project root and ensure that the dataset configuration folder exists.
    Debug logging is output to help trace the folder structure.
    """

    config_folder = project_root / "dataset_config"

    logging.debug(f"Project root: {project_root}")
    logging.debug(f"Config folder path: {config_folder}")

    if not config_folder.exists():
        try:
            logging.debug("Creating config folder...")
            config_folder.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Successfully created config folder at: {config_folder}")
        except Exception as e:
            st.error(f"Failed to create config folder: {e}")
    else:
        logging.debug("Config folder exists. Contents:")
        try:
            for item in config_folder.iterdir():
                item_type = "Directory" if item.is_dir() else "File"
                logging.debug(f"- {item.name} ({item_type})")
        except Exception as e:
            logging.error(f"Error listing config folder: {e}")
    return config_folder


class DatasetManager:
    def __init__(self, project_root: Union[str, Path]) -> None:
        # Allow config_folder to be passed as either a string or a Path.
        self.project_root = Path(project_root) if isinstance(project_root, str) else project_root
        self.config_folder = initialize_config_folder(self.project_root)
        # self.config_folder = Path(config_folder) if isinstance(config_folder, str) else config_folder
        self.api_client = self._initialize_api_client()

    def _initialize_config_folder(self) -> Path:
        """
        Resolve the project root and ensure that the dataset configuration folder exists.
        Debug logging is output to help trace the folder structure.
        """

        config_folder = self.project_root / "dataset_config"

        logging.debug(f"Project root: {self.project_root}")
        logging.debug(f"Config folder path: {config_folder}")

        if not config_folder.exists():
            try:
                logging.debug("Creating config folder...")
                config_folder.mkdir(parents=True, exist_ok=True)
                logging.debug(f"Successfully created config folder at: {config_folder}")
            except Exception as e:
                st.error(f"Failed to create config folder: {e}")
        else:
            logging.debug("Config folder exists. Contents:")
            try:
                for item in config_folder.iterdir():
                    item_type = "Directory" if item.is_dir() else "File"
                    logging.debug(f"- {item.name} ({item_type})")
            except Exception as e:
                logging.error(f"Error listing config folder: {e}")
        return config_folder

    def _initialize_api_client(self) -> APIClient:
        # You can switch between test and production credentials by commenting/uncommenting below.
        # client_id = os.getenv("LUXS_ACCEPT_CLIENT_ID")
        # client_secret = os.getenv("LUXS_ACCEPT_CLIENT_SECRET")
        # base_url = "https://api.accept.luxsinsights.com"

        client_id = os.getenv("LUXS_PROD_CLIENT_ID")
        client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET")
        base_url = os.getenv("LUXS_PROD_BASE_URL")
        token_url = os.getenv("LUXS_PROD_TOKEN_URL")

        return APIClient(client_id=client_id, client_secret=client_secret, base_url=base_url, token_url=token_url)

    def _load_configs(self) -> List[Dict[str, Any]]:
        """Load all JSON config files from the configuration folder."""
        configs = []
        for config_file in self.config_folder.glob("*.json"):
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                # Save the filename (without extension) for later use.
                data["__filename__"] = config_file.stem
                configs.append(data)
            except Exception as e:
                logging.error(f"Error reading config file {config_file}: {e}")
        return configs

    def get_available_datasets(self) -> List[str]:
        configs = self._load_configs()
        # Prepend a selection prompt to the list.
        datasets = [cfg.get("dataset") for cfg in configs if "dataset" in cfg]
        return datasets

    def get_dataset_config(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                return cfg
        return None

    def get_object_type(self, dataset_name: str) -> Optional[str]:
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                return cfg.get("objectType")
        return None

    def get_file_name(self, dataset_name: str) -> Optional[str]:
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                # Return the filename stored in the config (without .json)
                return cfg.get("__filename__")
        return None
