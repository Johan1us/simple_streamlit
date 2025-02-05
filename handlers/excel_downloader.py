import logging

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# Importeer de benodigde helpers en API-client
from utils.api_client import APIClient
from utils.excel_utils import ExcelHandler
from utils.metadata_handler import build_metadata_map


# Stel logging in op DEBUG-niveau voor gedetailleerde informatie
logging.basicConfig(level=logging.DEBUG)

class ExcelDownloader:
    """
    Klasse voor het genereren (downloaden) van een Excel-bestand op basis van een datasetconfiguratie.
    """

    def __init__(self, config: Dict[str, Any], api_client: APIClient):
        self.config = config
        self.api_client = api_client

    def generate_excel(self) -> bytes:
        """
        Genereer een Excel-bestand met data uit de API.
        """
        object_type = self.config["objectType"]
        attribute_names = [attr["AttributeName"] for attr in self.config.get("attributes", [])]

        # Haal metadata en data op via de API
        metadata = self.api_client.get_metadata(object_type)
        st.success("Metadata opgehaald van de API")
        response_data = self.api_client.get_all_objects(
            object_type=object_type,
            attributes=attribute_names,
            only_active=True,
            st=st,
        )
        st.success("Dataset opgehaald van de API")
        dataset_data = response_data.get("objects", [])
        logging.debug(f"Aantal objecten: {len(dataset_data)}")
        if dataset_data:
            logging.debug(f"Eerste object (voorbeeld): {dataset_data[0]}")

        # Bouw een mapping van Excel-kolomnamen naar API-veld namen
        columns_mapping = {
            attr["excelColumnName"]: attr["AttributeName"]
            for attr in self.config.get("attributes", [])
        }
        metadata_map = build_metadata_map(metadata, self.config)

        # Genereer het Excel-bestand
        handler = ExcelHandler(
            metadata=metadata_map,
            columns_mapping=columns_mapping,
            object_type=object_type
        )
        excel_file = handler.create_excel_file(data=dataset_data)

        # Toon een preview van de eerste 5 rijen van het Excel-bestand
        st.write("Preview van de eerste 5 rijen van de Excel file:")
        preview_df = pd.read_excel(excel_file)
        st.dataframe(preview_df.head(5), hide_index=True)

        return excel_file