import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import streamlit as st

# Configureer de logging module zodat debug-informatie zichtbaar wordt
logging.basicConfig(level=logging.DEBUG)


def get_object_type_data(metadata: Dict[str, Any], object_type: str) -> Dict[str, Any]:
    """
    Zoekt en retourneert de data voor een specifiek objecttype in de metadata.

    Parameters:
        metadata (dict): De metadata met alle objecttypes.
        object_type (str): De naam van het gewenste objecttype.

    Returns:
        dict: De data voor het opgegeven objecttype.

    Raises:
        ValueError: Als het objecttype niet gevonden wordt.
    """
    ot_data = next(
        (ot for ot in metadata.get("objectTypes", []) if ot.get("name") == object_type),
        None
    )
    if not ot_data:
        raise ValueError(f"Object type {object_type} niet gevonden in metadata")
    return ot_data


def create_attribute_mapping(attributes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bouwt een mapping op van attributen naar hun metadata, waarbij zowel de volledige naam
    als een vereenvoudigde naam (zonder eventuele suffix) wordt opgeslagen.

    Parameters:
        attributes (list): Een lijst van attributen, elk met een 'name' veld.

    Returns:
        dict: Mapping van zowel volledige als vereenvoudigde namen naar de bijbehorende metadata.
    """
    mapping = {}
    for attr in attributes:
        # Haal de volledige naam van het attribuut op
        full_name = attr["name"]
        # Als er een ' - ' in voorkomt, splitsen we op en gebruiken we het eerste deel als eenvoudige naam
        simple_name = full_name.split(" - ")[0] if " - " in full_name else full_name
        mapping[full_name] = attr
        mapping[simple_name] = attr
    return mapping


def map_config_attributes_to_metadata(
    config_attributes: List[Dict[str, Any]], attribute_mapping: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Koppelt de attributen uit de configuratie aan de bijbehorende metadata.

    Parameters:
        config_attributes (list): Lijst van attributen uit de configuratie, elk met 'AttributeName'.
        attribute_mapping (dict): Mapping van attribuutnamen naar metadata.

    Returns:
        dict: Mapping van de configuratie attribuutnaam naar de bijbehorende metadata.
    """
    meta_map = {}
    for attr_def in config_attributes:
        attr_name = attr_def["AttributeName"]
        # Zoek de metadata voor dit attribuut; als deze niet bestaat, wordt een lege dict gebruikt
        meta = attribute_mapping.get(attr_name, {})
        meta_map[attr_name] = meta
    return meta_map


def build_metadata_map(metadata: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bouwt een mapping op van metadata voor elk attribuut zoals gespecificeerd in de configuratie.

    Parameters:
        metadata (dict): De originele metadata met informatie over objecttypes en hun attributen.
        config (dict): De configuratie met onder andere het gewenste objecttype en de attributen.

    Returns:
        dict: Een mapping waarbij de sleutel de naam van een attribuut is en de waarde de bijbehorende metadata.
    """
    # Haal het gewenste objecttype op uit de configuratie
    object_type = config["objectType"]

    # Zoek in de metadata naar de data voor het opgegeven objecttype
    ot_data = get_object_type_data(metadata, object_type)

    # Maak een mapping van attribuutnamen naar metadata op basis van het objecttype
    attribute_mapping = create_attribute_mapping(ot_data.get("attributes", []))

    # Koppel de attributen uit de configuratie aan de bijbehorende metadata
    return map_config_attributes_to_metadata(config.get("attributes", []), attribute_mapping)

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