import logging
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from vip_datamakelaar.utils.validation import ExcelValidator
from utils.dataset_manager import DatasetManager
from utils.data_type_mapper import DataTypeMapper
from utils.metadata_handler import build_metadata_map

logging.basicConfig(level=logging.DEBUG)


def prepare_data_to_send(
        df: pd.DataFrame,
        columns_mapping: Dict[str, str],
        object_type: str,
        metadata_map: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Prepare the list of objects to send to the API based on the uploaded Excel file."""
    if "identifier" not in df.columns:
        raise ValueError("Geen 'identifier' kolom gevonden in de data!")

    # Initialize the data type mapper
    type_mapper = DataTypeMapper(metadata_map)

    data_to_send = []
    for _, row in df.iterrows():
        attributes = {}
        for col, api_field in columns_mapping.items():
            original_value = row[col]
            field_metadata = metadata_map.get(api_field, {})
            new_value = type_mapper.convert_value(col, api_field, original_value, field_metadata)
            attributes[api_field] = new_value

        data_to_send.append({
            "objectType": object_type,
            "identifier": str(row["identifier"]),
            "attributes": attributes
        })
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


def handle_excel_upload(config: Dict[str, Any], dataset_manager: DatasetManager, selected_dataset: str) -> None:
    """Handle the Excel upload, validation, and (if validated) upload to the API."""
    # Set pandas display options to prevent thousand separators
    pd.options.display.float_format = '{:.0f}'.format

    excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
    if not excel_file:
        return

    st.success("Excel file is geüpload")

    try:
        metadata = dataset_manager.api_client.get_metadata(config["objectType"])
    except Exception as e:
        st.error(f"Error getting metadata: {e}")
        return

    # Create a dtype mapping for pandas based on metadata
    columns_mapping = {attr["excelColumnName"]: attr["AttributeName"] for attr in config.get("attributes", [])}
    dtype_mapping = {}
    date_format_mapping = {}

    # Get the object type attributes from metadata
    object_type_data = metadata["objectTypes"][0]
    attributes = object_type_data["attributes"]

    # Create mapping of Excel column names to their expected types
    for excel_col, api_field in columns_mapping.items():
        field_metadata = next((attr for attr in attributes if attr["name"] == api_field), None)
        if field_metadata:
            field_type = field_metadata.get("type", "").upper()
            # Map metadata types to pandas dtypes
            if field_type == "STRING":
                dtype_mapping[excel_col] = str
            elif field_type == "INT":
                dtype_mapping[excel_col] = "Int64"
            elif field_type == "DATE":
                # For dates, we'll initially read as string
                dtype_mapping[excel_col] = str
                # Store the date format
                date_format_mapping[excel_col] = field_metadata.get("dateFormat")

    # Read Excel with the specified dtypes
    df = pd.read_excel(excel_file, dtype=dtype_mapping)

    # Convert date columns based on their formats
    for col, date_format in date_format_mapping.items():
        if col in df.columns:
            try:
                if date_format == "yyyy":
                    # For year format, keep as string to prevent numeric formatting
                    df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True)
                    # Remove any commas that might have been added
                    df[col] = df[col].str.replace(',', '')
                elif date_format == "dd-MM-yyyy":
                    df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
                elif date_format == "yyyy-MM-dd":
                    df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
            except Exception as e:
                st.warning(f"Could not convert column {col} to date format {date_format}: {str(e)}")

    # Create validator before using it
    object_type = dataset_manager.get_object_type(selected_dataset)
    metadata_map = build_metadata_map(metadata, config)
    validator = ExcelValidator(metadata=metadata_map, columns_mapping=columns_mapping, object_type=object_type)

    st.subheader("Expected Column Types")
    meta_data = []
    for api_name, excel_name in validator.reverse_mapping.items():
        # Find the matching attribute in the original metadata
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
            data_to_send = prepare_data_to_send(df_clean, columns_mapping, object_type, metadata_map)
            upload_to_vip(dataset_manager, object_type, data_to_send)


