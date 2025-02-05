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

logging.basicConfig(level=logging.DEBUG)


class DatasetManager:
    def __init__(self, config_folder: Union[str, Path]) -> None:
        # Allow config_folder to be passed as either a string or a Path.
        self.config_folder = Path(config_folder) if isinstance(config_folder, str) else config_folder
        self.api_client = self._initialize_api_client()

    def _initialize_api_client(self) -> APIClient:
        # You can switch between test and production credentials by commenting/uncommenting below.
        # client_id = os.getenv("LUXS_ACCEPT_CLIENT_ID")
        # client_secret = os.getenv("LUXS_ACCEPT_CLIENT_SECRET")
        # base_url = "https://api.accept.luxsinsights.com"

        client_id = os.getenv("LUXS_PROD_CLIENT_ID")
        client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET")
        base_url = "https://api.prod.luxsinsights.com"

        return APIClient(client_id=client_id, client_secret=client_secret, base_url=base_url)

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
        return ["Selecteer dataset"] + datasets

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


def show_dataset_fields(config: Dict[str, Any]) -> None:
    """Display the Excel column names that will be used."""
    excel_columns = [attr["excelColumnName"] for attr in config.get("attributes", [])]
    df = pd.DataFrame(excel_columns, columns=["Velden :"])
    st.dataframe(df, hide_index=True)


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


def build_metadata_map(metadata: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a mapping of metadata for each attribute in the configuration."""
    object_type = config["objectType"]
    ot_data = next(
        (ot for ot in metadata.get("objectTypes", []) if ot.get("name") == object_type), None
    )
    if not ot_data:
        raise ValueError(f"Object type {object_type} not found in metadata")

    # Create a more flexible mapping that matches on partial names
    metadata_by_name = {}
    for attr in ot_data.get("attributes", []):
        # Store both the full name and a simplified version (without the suffix)
        full_name = attr["name"]
        simple_name = full_name.split(" - ")[0] if " - " in full_name else full_name
        metadata_by_name[full_name] = attr
        metadata_by_name[simple_name] = attr

    meta_map = {}
    for attr_def in config.get("attributes", []):
        attr_name = attr_def["AttributeName"]
        meta = metadata_by_name.get(attr_name, {})
        meta_map[attr_name] = meta
    return meta_map


def convert_cell_value(
    col: str, api_field: str, value: Any, jaar_attribute: Optional[Dict[str, Any]]
) -> Optional[Union[int, str]]:
    """
    Convert a value read from the Excel cell to the expected format for the API.
    Special handling is provided for fields like 'WOZ waarde' and onderhoudsvelden.
    """
    if "WOZ waarde" in col:
        if pd.notnull(value):
            st.write(f"Debug WOZ waarde:\n- Original value: {value}\n- Type: {type(value)}")
            converted = int(float(value))
            st.write(f"- Converted value: {converted}")
            return converted
    elif ("laatste dakonderhoud" in api_field.lower() or "laatste gevelonderhoud" in api_field.lower()) and pd.notnull(value):
        try:
            if jaar_attribute and jaar_attribute.get("dateFormat") == "yyyy":
                return str(int(float(value)))
            else:
                year = int(float(value))
                date_format = jaar_attribute.get("dateFormat", "dd-MM-yyyy") if jaar_attribute else "dd-MM-yyyy"
                if date_format == "dd-MM-yyyy":
                    return f"31-12-{year}"
                elif date_format == "yyyy-MM-dd":
                    return f"{year}-12-31"
                else:
                    return str(year)
        except Exception as e:
            st.write(f"Fout bij verwerking jaartal: {e}")
            return None
    elif isinstance(value, float) and pd.notnull(value):
        # If the float is really an integer, convert it.
        if value.is_integer():
            return int(value)
        else:
            return str(value)
    elif pd.notnull(value):
        return str(value)
    return None


def prepare_data_to_send(
    df: pd.DataFrame, columns_mapping: Dict[str, str], object_type: str, jaar_attribute: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Prepare the list of objects to send to the API based on the uploaded Excel file."""
    if "identifier" not in df.columns:
        raise ValueError("Geen 'identifier' kolom gevonden in de data!")
    data_to_send = []
    for _, row in df.iterrows():
        attributes = {}
        for col, api_field in columns_mapping.items():
            original_value = row[col]
            new_value = convert_cell_value(col, api_field, original_value, jaar_attribute)
            attributes[api_field] = new_value
        data_to_send.append(
            {"objectType": object_type, "identifier": str(row["identifier"]), "attributes": attributes}
        )
    return data_to_send


def upload_to_vip(
    dataset_manager: DatasetManager, object_type: str, data_to_send: List[Dict[str, Any]]
) -> None:
    """Send the prepared data to the API and display a report of the upload."""
    try:
        response = dataset_manager.api_client.update_objects(objects_data=data_to_send)
        if response:
            response_objects = response.get("objects", [])
            failed_updates = [r for r in response_objects if not r.get("success")]
            if failed_updates:
                st.error("❌ Mislukte updates:")
                for fail in failed_updates:
                    st.write(f"- Object {fail.get('identifier')}: {fail.get('message')}")
            st.success(
                f"✅ Upload Rapport:\n- Totaal aantal objecten: {len(response_objects)}\n"
                f"- Succesvol bijgewerkt: {sum(1 for r in response_objects if r.get('success'))}\n"
                f"- Mislukt: {sum(1 for r in response_objects if not r.get('success'))}"
            )
    except Exception as e:
        st.error(f"❌ Er is een fout opgetreden: {e}")
        st.write("Debug informatie:")


def initialize_config_folder() -> Path:
    """
    Resolve the project root and ensure that the dataset configuration folder exists.
    Debug logging is output to help trace the folder structure.
    """
    file_folder = Path(__file__).resolve().parent
    project_root = file_folder.parent
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


def handle_excel_upload(config: Dict[str, Any], dataset_manager: DatasetManager, selected_dataset: str) -> None:
    """Handle the Excel upload, validation, and (if validated) upload to the API."""
    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if not excel_file:
        return

    st.success("Excel file is geüpload")

    try:
        metadata = dataset_manager.api_client.get_metadata(config["objectType"])
    except Exception as e:
        st.error(f"Error getting metadata: {e}")
        return

    st.write(metadata)

    columns_mapping = {attr["excelColumnName"]: attr["AttributeName"] for attr in config.get("attributes", [])}
    validator = ExcelValidator(metadata, columns_mapping, config["objectType"])

    st.subheader("Expected Column Types")
    meta_data = []
    for api_name, excel_name in validator.reverse_mapping.items():
        # Navigate through the nested structure
        object_type_data = validator.metadata["objectTypes"][0]  # Get the first object type
        attributes = object_type_data["attributes"]
        
        # Find the matching attribute
        field_metadata = next(
            (attr for attr in attributes if attr["name"] == api_name),
            {}
        )
        
        meta_data.append({
            "Excel Column": excel_name,
            "Expected Type": field_metadata.get("type", "UNKNOWN").upper(),
            "Required": "Yes" if field_metadata.get("required", False) else "No",
            "Format": field_metadata.get("dateFormat", "-") if field_metadata.get("type") == "DATE" else "-",
            "Definition": field_metadata.get("definition", "-")
        })

    meta_df = pd.DataFrame(meta_data)
    st.dataframe(meta_df, use_container_width=True)

    st.subheader("Excel Preview")
    df = pd.read_excel(excel_file)
    st.write("Preview van de geüploade Excel:")
    st.dataframe(df.head(5), hide_index=True)

    # Retrieve object type and metadata needed for special field conversions.
    object_type = dataset_manager.get_object_type(selected_dataset)
    metadata = dataset_manager.api_client.get_metadata(object_type)

    # Zoek het jaartal attribuut in de metadata.
    jaar_attribute = None
    object_types = metadata.get("objectTypes", [])
    if object_types:
        for attr in object_types[0].get("attributes", []):
            if any(x in attr.get("name", "").lower() for x in ["laatste dakonderhoud", "laatste gevelonderhoud"]):
                jaar_attribute = attr
                break

    # Rebuild metadata map and the columns mapping (as in the download handler).
    columns_mapping = {attr["excelColumnName"]: attr["AttributeName"] for attr in config.get("attributes", [])}
    metadata_map = build_metadata_map(metadata, config)
    validator = ExcelValidator(metadata=metadata_map, columns_mapping=columns_mapping, object_type=object_type)
    validation_errors = validator.validate_excel(df)

    if validation_errors:
        st.error("De Excel bevat de volgende fouten:")
        error_df = pd.DataFrame(validation_errors)
        st.dataframe(error_df, hide_index=True)
    else:
        st.success("De Excel is succesvol gevalideerd! Alle data voldoet aan de vereisten.")
        if st.button("Upload naar VIP"):
            df_clean = df.replace([float("inf"), float("-inf"), float("nan")], None)
            st.write("Debug - DataFrame types:")
            st.write(df_clean.dtypes)
            st.write("\nDebug - First row raw values:")
            st.write(df_clean.iloc[0])
            data_to_send = prepare_data_to_send(df_clean, columns_mapping, object_type, jaar_attribute)
            upload_to_vip(dataset_manager, object_type, data_to_send)


def show_home() -> None:
    """Main function for the Streamlit page."""
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Uitloggen", key="logout_btn"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()  # Use experimental_rerun for restarting the app.

    with col1:
        st.title("VIP DataMakelaar")

    st.header("Stap 1: Selecteer een dataset")

    # Initialize and ensure the configuration folder exists.
    config_folder = initialize_config_folder()
    dataset_manager = DatasetManager(config_folder)
    datasets = dataset_manager.get_available_datasets()
    selected_dataset = st.selectbox("Dataset", datasets, index=0)

    if selected_dataset and selected_dataset != "Geen dataset geselecteerd":
        config = dataset_manager.get_dataset_config(selected_dataset)
        if config:
            show_dataset_fields(config)

            st.header("Stap 2: Download Excel")
            if st.button("Geneer Excel"):
                file_name = dataset_manager.get_file_name(selected_dataset) or "download"
                st.write(f"Excel voor {selected_dataset} wordt gegenereerd...")
                try:
                    excel_file = handle_excel_download(config, dataset_manager.api_client)
                    st.download_button(
                        label="Download Excel",
                        data=excel_file,
                        file_name=f"{file_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error("❌ Er is een fout opgetreden bij het genereren van de Excel:")
                    st.error(f"Foutmelding: {e}")
                    with st.expander("Technische details", expanded=False):
                        st.write("📋 Debug informatie:")
                        st.write(f"- Dataset: {selected_dataset}")
                        st.write(f"- Bestandsnaam: {file_name}")
                        st.write(f"- Object Type: {config.get('objectType', 'Niet gevonden')}")
                        st.write(f"- Aantal attributen: {len(config.get('attributes', []))}")
                        st.write(f"- Type fout: {type(e).__name__}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")
                    st.info("💡 Suggestie: Controleer of alle benodigde configuraties correct zijn en of er verbinding is met de API.")

            st.header("Stap 3: Upload Excel")
            handle_excel_upload(config, dataset_manager, selected_dataset)
