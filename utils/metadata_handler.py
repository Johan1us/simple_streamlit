import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import streamlit as st



logging.basicConfig(level=logging.DEBUG)

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

class DataTypeMapper:
    """
    Class responsible for converting values between Excel and API formats based on metadata.
    """

    def __init__(self, metadata_map: Dict[str, Any]):
        self.metadata_map = metadata_map

    def convert_value(self, value: Any, field_metadata: Dict[str, Any]) -> Optional[
        Union[int, str]]:
        """
        Convert a value based on its metadata type and format.

        Args:
            col: Excel column name
            api_field: API field name
            value: Value to convert
            field_metadata: Metadata for this field from the API
        """
        if pd.isnull(value):
            return None

        field_type = field_metadata.get("type", "").upper()

        # Dispatch to appropriate conversion method based on type
        if field_type == "DATE":
            return self._convert_date(value, field_metadata.get("dateFormat"))
        elif field_type == "INT":
            return self._convert_int(value)
        elif field_type == "FLOAT":
            return self._convert_float(value)
        else:
            return self._convert_string(value)

    def _convert_date(self, value: Any, date_format: Optional[str]) -> Optional[str]:
        """Convert a value to the specified date format."""
        try:
            # Convert to datetime if not already
            if not isinstance(value, pd.Timestamp):
                value = pd.to_datetime(value)

            # Format according to specified format
            if date_format == "yyyy":
                return str(value.year)
            elif date_format == "dd-MM-yyyy":
                return value.strftime("%d-%m-%Y")
            elif date_format == "yyyy-MM-dd":
                return value.strftime("%Y-%m-%d")
            else:
                return value.strftime("%Y-%m-%d")  # default format

        except Exception as e:
            st.write(f"Error converting date value {value}: {e}")
            return None

    def _convert_int(self, value: Any) -> Optional[int]:
        """Convert a value to integer."""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            st.write(f"Error converting {value} to integer")
            return None

    def _convert_float(self, value: Any) -> Union[int, str]:
        """Convert a value to float/integer."""
        try:
            float_val = float(value)
            # Return as integer if it's a whole number
            return int(float_val) if float_val.is_integer() else str(float_val)
        except (ValueError, TypeError):
            return str(value)

    def _convert_string(self, value: Any) -> str:
        """Convert a value to string."""
        return str(value)