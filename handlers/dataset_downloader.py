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

class DatasetDownloader:
    """
    Klasse voor het genereren (downloaden) van een Excel-bestand op basis van een datasetconfiguratie.
    """

    def __init__(self, config: Dict[str, Any], api_client: APIClient, complex_selectie: List[str]):
        """
        Initialiseer de DatasetDownloader met de configuratie, API-client en filter parameters.
        """
        self.config = config
        self.api_client = api_client
        self.complex_selectie = complex_selectie

    def generate_excel(self) -> bytes:
        """
        Genereer een Excel-bestand met data uit de API.
        
        Returns:
            bytes: Excel bestand als bytes object
        """
        object_type = self.config["objectType"]
        attribute_names = [attr["AttributeName"] for attr in self.config.get("attributes", [])]

        # Haal metadata op via de API
        try:
            metadata = self.api_client.get_metadata(object_type)
            st.success("Metadata opgehaald van de API")
        except Exception as e:
            st.error(f"Fout bij ophalen metadata: {str(e)}")
            raise

        # Initialize empty list to store all data
        all_dataset_data = []

        # Check if complex_selectie exists and handle data fetching accordingly
        if self.complex_selectie:
            # Loop through each complex and make separate API calls
            for complex_id in self.complex_selectie:
                print("="*50)
                print(f"Processing complex_id: {complex_id}")
                filter_params = {"Cluster": complex_id}
                print(f"Filter params being sent: {filter_params}")
                try:
                    print("Before API call")
                    response_data = self.api_client.get_all_objects(
                        object_type=object_type,
                        attributes=attribute_names,
                        only_active=True,
                        filter_params=filter_params,
                        st=st,
                    )
                    print("After API call")
                    print(f"Response data keys: {response_data.keys()}")
                    print(f"Number of objects in response: {len(response_data.get('objects', []))}")
                    all_dataset_data.extend(response_data.get("objects", []))
                    st.success(f"Data opgehaald voor complex: {complex_id}")
                except Exception as e:
                    print(f"ERROR for complex {complex_id}: {str(e)}")
                    st.error(f"Fout bij ophalen data voor complex {complex_id}: {str(e)}")
                    raise
        else:
            # Fetch all data without complex filtering
            try:
                response_data = self.api_client.get_all_objects(
                    object_type=object_type,
                    attributes=attribute_names,
                    only_active=True,
                    filter_params={},
                    st=st,
                )
                all_dataset_data.extend(response_data.get("objects", []))
                st.success("Data succesvol opgehaald")
            except Exception as e:
                st.error(f"Fout bij ophalen data: {str(e)}")
                raise

        logging.debug(f"Totaal aantal objecten: {len(all_dataset_data)}")
        if all_dataset_data:
            logging.debug(f"Eerste object (voorbeeld): {all_dataset_data[0]}")

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
        excel_file = handler.create_excel_file(data=all_dataset_data)

        # Toon een preview van de eerste 5 rijen van het Excel-bestand
        st.write("Preview van de eerste 5 rijen van de Excel file:")
        preview_df = pd.read_excel(excel_file)
        st.dataframe(preview_df.head(5), hide_index=True)

        return excel_file