import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import streamlit as st

from vip_datamakelaar.utils.api_client import APIClient
from vip_datamakelaar.utils.excel_utils import ExcelHandler
from vip_datamakelaar.utils.validation import ExcelValidator
from utils.dataset_manager import DatasetManager
from utils.data_type_mapper import DataTypeMapper
from utils.metadata_handler import build_metadata_map

logging.basicConfig(level=logging.DEBUG)

def handle_excel_download(config: Dict[str, Any], api_client: APIClient) -> bytes:
    """Download the dataset from the API and create an Excel file."""
    object_type = config["objectType"]
    attribute_names = [attr["AttributeName"] for attr in config.get("attributes", [])]

    # Retrieve metadata and data from the API.
    metadata = api_client.get_metadata(object_type)
    st.success("Metadata opgehaald van de API")
    response_data = api_client.get_all_objects(
        object_type=object_type,
        attributes=attribute_names,
        only_active=True,
        st=st,
    )
    st.success("Dataset opgehaald van de API")

    dataset_data = response_data.get("objects", [])
    logging.debug(f"Number of objects: {len(dataset_data)}")
    if dataset_data:
        logging.debug(f"First object sample: {dataset_data[0]}")

    columns_mapping = {attr["excelColumnName"]: attr["AttributeName"] for attr in config.get("attributes", [])}
    metadata_map = build_metadata_map(metadata, config)

    handler = ExcelHandler(metadata=metadata_map, columns_mapping=columns_mapping, object_type=object_type)
    excel_file = handler.create_excel_file(data=dataset_data)

    st.write("Preview van de eerste 5 rijen van de Excel file:")
    preview_df = pd.read_excel(excel_file)
    st.dataframe(preview_df.head(5), hide_index=True)

    return excel_file