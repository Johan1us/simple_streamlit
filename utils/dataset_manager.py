import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import streamlit as st

from utils.api_client import APIClient

# Stel logging in op DEBUG-niveau zodat we uitgebreide informatie krijgen tijdens het uitvoeren van de code.
logging.basicConfig(level=logging.DEBUG)


def initialize_config_folder(project_root: Union[str, Path]) -> Path:
    """
    Zorgt ervoor dat de configuratiemap voor datasets bestaat.
    Als de map nog niet bestaat, wordt deze aangemaakt.

    :param project_root: De hoofdmap van het project (als een string of Path).
    :return: Het Path-object dat verwijst naar de dataset configuratiemap.
    """
    # Zorg dat project_root een Path-object is (ook als het als string is doorgegeven)
    if isinstance(project_root, str):
        project_root = Path(project_root)

    # Bepaal het pad naar de dataset configuratiemap
    config_folder = project_root / "dataset_config"

    # Log informatie over de project root en het pad naar de configuratiemap
    logging.debug(f"Project root: {project_root}")
    logging.debug(f"Config folder path: {config_folder}")

    # Als de configuratiemap niet bestaat, maak deze dan aan
    if not config_folder.exists():
        try:
            logging.debug("Configuratiemap bestaat niet. Wordt aangemaakt...")
            config_folder.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Configuratiemap succesvol aangemaakt op: {config_folder}")
        except Exception as e:
            st.error(f"Fout bij het aanmaken van de configuratiemap: {e}")
    else:
        # Als de map al bestaat, log dan de inhoud van de map
        logging.debug("Configuratiemap bestaat. Inhoud van de map:")
        try:
            for item in config_folder.iterdir():
                # Bepaal of het item een map of een bestand is
                item_type = "Map" if item.is_dir() else "Bestand"
                logging.debug(f"- {item.name} ({item_type})")
        except Exception as e:
            logging.error(f"Fout bij het weergeven van de inhoud van de configuratiemap: {e}")

    return config_folder


class DatasetManager:
    """
    Deze klasse beheert de dataset configuraties.
    Het zorgt ervoor dat de configuratiemap bestaat, laadt configuratiebestanden in
    en biedt methoden om specifieke informatie uit deze configuraties op te halen.
    """

    def __init__(self, project_root: Union[str, Path], api_client: APIClient) -> None:
        """
        Initialiseert de DatasetManager.

        :param project_root: De hoofdmap van het project (als een string of Path).
        :param api_client: Een instantie van APIClient voor API-communicatie.
        """
        # Zorg dat project_root een Path-object is
        if isinstance(project_root, str):
            self.project_root = Path(project_root)
        else:
            self.project_root = project_root

        # Initialiseer de configuratiemap met behulp van de centrale functie
        self.config_folder = initialize_config_folder(self.project_root)
        self.api_client = api_client

    def _load_configs(self) -> List[Dict[str, Any]]:
        """
        Laad alle JSON-configuratiebestanden uit de configuratiemap.

        :return: Een lijst van dictionaries, waarbij elk dictionary één configuratie voorstelt.
        """
        configs = []
        # Zoek naar alle .json bestanden in de configuratiemap
        for config_file in self.config_folder.glob("*.json"):
            try:
                # Lees de inhoud van het JSON-bestand en zet deze om in een dictionary
                data = json.loads(config_file.read_text(encoding="utf-8"))
                # Voeg de bestandsnaam (zonder extensie) toe aan de dictionary voor later gebruik
                data["__filename__"] = config_file.stem
                configs.append(data)
            except Exception as e:
                logging.error(f"Fout bij het lezen van configuratiebestand {config_file}: {e}")
        return configs

    def get_available_datasets(self) -> List[str]:
        """
        Haal een lijst op met de namen van alle beschikbare datasets.

        :return: Een lijst met dataset namen.
        """
        configs = self._load_configs()
        # Haal uit elke configuratie de waarde op van de sleutel "dataset" (indien aanwezig)
        datasets = [cfg.get("dataset") for cfg in configs if "dataset" in cfg]
        return datasets

    def get_dataset_config(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """
        Zoek en retourneer de configuratie voor een specifieke dataset.

        :param dataset_name: De naam van de dataset.
        :return: De configuratie als dictionary, of None als deze niet gevonden is.
        """
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                return cfg
        return None

    def get_object_type(self, dataset_name: str) -> Optional[str]:
        """
        Haal het objecttype op voor een specifieke dataset.

        :param dataset_name: De naam van de dataset.
        :return: Het objecttype als string, of None als niet gevonden.
        """
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                return cfg.get("objectType")
        return None

    def get_file_name(self, dataset_name: str) -> Optional[str]:
        """
        Haal de bestandsnaam (zonder extensie) op voor de configuratie van een specifieke dataset.

        :param dataset_name: De naam van de dataset.
        :return: De bestandsnaam als string, of None als niet gevonden.
        """
        for cfg in self._load_configs():
            if cfg.get("dataset") == dataset_name:
                return cfg.get("__filename__")
        return None
