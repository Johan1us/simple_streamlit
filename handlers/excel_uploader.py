import logging
from typing import Any, Dict, List, Tuple, Optional
import pandas as pd
import streamlit as st

# Importeer de benodigde helpers en API-client
from utils.metadata_handler import build_metadata_map, DataTypeMapper
from utils.dataset_config import DatasetConfig
from utils.validation import ExcelValidator

# Stel logging in op DEBUG-niveau voor gedetailleerde informatie
logging.basicConfig(level=logging.DEBUG)


# ------------------------------
# Stap 1: Upload Excel-bestand
# ------------------------------
class ExcelUploadStep1:
    """
    Stap 1: Laat de gebruiker een Excel-bestand uploaden.
    """

    def upload_excel_file(self) -> Optional[Any]:
        excel_file = st.file_uploader("Upload Excel", type=["xlsx"])
        if excel_file:
            st.success("Excel file is geüpload")
        return excel_file


# -----------------------------------------------
# Stap 2: Haal metadata op en bouw de mappings
# -----------------------------------------------
class ExcelUploadStep2:
    """
    Stap 2: Haal metadata op via de API en bouw de benodigde mappings
    voor Excel-kolomnamen naar API-veld namen, inclusief datatype- en
    datumformaat mapping.
    """

    def __init__(self, config: Dict[str, Any], dataset_config: DatasetConfig):
        self.config = config
        self.dataset_config = dataset_config

    def get_metadata_and_mappings(self) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        try:
            metadata = self.dataset_config.api_client.get_metadata(self.config["objectType"])
        except Exception as e:
            st.error(f"Error getting metadata: {e}")
            return {}, {}, {}, {}

        # Bouw een mapping van Excel-kolomnamen naar API-veld namen
        columns_mapping = {
            attr["excelColumnName"]: attr["AttributeName"]
            for attr in self.config.get("attributes", [])
        }
        dtype_mapping = {}
        date_format_mapping = {}
        attributes = metadata["objectTypes"][0]["attributes"]
        for excel_col, api_field in columns_mapping.items():
            field_metadata = next((attr for attr in attributes if attr["name"] == api_field), None)
            if field_metadata:
                field_type = field_metadata.get("type", "").upper()
                if field_type == "STRING":
                    dtype_mapping[excel_col] = str
                elif field_type == "INT":
                    dtype_mapping[excel_col] = "Int64"
                elif field_type == "DATE":
                    # Lees datumkolommen als string; conversie volgt later
                    dtype_mapping[excel_col] = str
                    date_format_mapping[excel_col] = field_metadata.get("dateFormat")
        return metadata, columns_mapping, dtype_mapping, date_format_mapping


# ------------------------------------------------------------
# Stap 3: Lees het Excel-bestand in en converteer datumkolommen
# ------------------------------------------------------------
class ExcelUploadStep3:
    """
    Stap 3: Lees het geüploade Excel-bestand in met de opgegeven datatypes
    en converteer de datumkolommen naar het juiste formaat.
    """

    def __init__(self, dtype_mapping: Dict[str, Any], date_format_mapping: Dict[str, Any]):
        self.dtype_mapping = dtype_mapping
        self.date_format_mapping = date_format_mapping

    def read_and_convert_excel(self, excel_file) -> pd.DataFrame:
        df = self._read_excel(excel_file, self.dtype_mapping)
        self._convert_date_columns(df, self.date_format_mapping)
        return df

    def _read_excel(self, file, dtype_mapping: Dict[str, Any]) -> pd.DataFrame:
        """Lees het Excel-bestand in met de opgegeven datatypes."""
        return pd.read_excel(file, dtype=dtype_mapping)

    def _convert_date_columns(self, df: pd.DataFrame, date_format_mapping: Dict[str, Any]) -> None:
        """Converteer datumkolommen naar het juiste formaat."""
        for col, date_format in date_format_mapping.items():
            if col in df.columns:
                try:
                    if date_format == "yyyy":
                        df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True)
                        df[col] = df[col].str.replace(',', '')
                    elif date_format in ["dd-MM-yyyy", "yyyy-MM-dd"]:
                        df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
                except Exception as e:
                    st.warning(f"Could not convert column {col} to date format {date_format}: {str(e)}")

    def show_preview(self, df: pd.DataFrame) -> None:
        """Toon een preview van de eerste 5 rijen van de ingelezen Excel-data."""
        st.subheader("Excel Preview")
        st.write("Preview van de geüploade Excel:")
        st.dataframe(df.head(30), hide_index=True)


# -------------------------------------------------
# Stap 4: Valideer de ingelezen Excel-data
# -------------------------------------------------
class ExcelUploadStep4:
    """
    Stap 4: Valideer de ingelezen Excel-data en toon de verwachte kolomtypes.
    """

    def __init__(self, config: Dict[str, Any], dataset_config: DatasetConfig,
                 selected_dataset: str, columns_mapping: Dict[str, str],
                 metadata: Dict[str, Any]):
        self.config = config
        self.dataset_config = dataset_config
        self.selected_dataset = selected_dataset
        self.columns_mapping = columns_mapping
        self.metadata = metadata

    def validate_excel(self, df: pd.DataFrame) -> bool:
        object_type_val = self.dataset_config.get_object_type(self.selected_dataset)
        metadata_map = build_metadata_map(self.metadata, self.config)
        validator = ExcelValidator(
            metadata=metadata_map,
            columns_mapping=self.columns_mapping,
            object_type=object_type_val
        )
        # self._show_expected_column_types(validator, self.metadata["objectTypes"][0]["attributes"])
        validation_errors = validator.validate_excel(df)
        if validation_errors:
            st.error("De Excel bevat de volgende fouten:")
            st.dataframe(pd.DataFrame(validation_errors), hide_index=True)
            return False
        st.success("De Excel is succesvol gevalideerd! Alle data voldoet aan de vereisten.")
        return True

    def _show_expected_column_types(self, validator: ExcelValidator, attributes: List[Dict[str, Any]]) -> None:
        """Toon een overzicht van de verwachte kolomtypes en formaten."""
        st.subheader("Expected Column Types")
        meta_data = []
        for api_name, excel_name in validator.reverse_mapping.items():
            field_metadata = next((attr for attr in attributes if attr["name"] == api_name), {})
            meta_data.append({
                "Excel Column": excel_name,
                "Expected Type": field_metadata.get("type", "UNKNOWN").upper(),
                "Required": "Yes" if field_metadata.get("required", False) else "No",
                "Format": field_metadata.get("dateFormat", "-") if field_metadata.get("type") == "DATE" else "-",
                "Definition": field_metadata.get("definition", "-")
            })
        meta_df = pd.DataFrame(meta_data)
        st.dataframe(meta_df, use_container_width=True)


# ----------------------------------------------
# Stap 5: Upload de gevalideerde data naar de API
# ----------------------------------------------
class ExcelUploadStep5:
    """
    Stap 5: Bereid de gevalideerde data voor en upload deze naar de API.
    """

    def __init__(self, config: Dict[str, Any], dataset_config: DatasetConfig,
                 selected_dataset: str, columns_mapping: Dict[str, str],
                 metadata: Dict[str, Any]):
        self.config = config
        self.dataset_config = dataset_config
        self.selected_dataset = selected_dataset
        self.columns_mapping = columns_mapping
        self.metadata = metadata

    def upload_data(self, df: pd.DataFrame) -> None:
        object_type_val = self.dataset_config.get_object_type(self.selected_dataset)
        metadata_map = build_metadata_map(self.metadata, self.config)
        # Vervang eventuele inf, -inf en NaN-waarden door None
        df_clean = df.replace([float("inf"), float("-inf"), float("nan")], None)
        # st.write("Debug - DataFrame types:")
        # st.write(df_clean.dtypes)
        # st.write("\nDebug - Eerste rij raw values:")
        # st.write(df_clean.iloc[0])
        data_to_send = self._prepare_data_to_send(df_clean, object_type_val, metadata_map)
        self._upload_to_vip(object_type_val, data_to_send)

    def _prepare_data_to_send(self, df: pd.DataFrame, object_type: str,
                              metadata_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "identifier" not in df.columns:
            raise ValueError("Geen 'identifier' kolom gevonden in de data!")
        type_mapper = DataTypeMapper(metadata_map)
        data_to_send = []

        dataset_config_data = self.dataset_config.get_dataset_config(self.selected_dataset)
        parent_object_type = dataset_config_data.get("parentObjectType")
        parent_identifier_excel_column = dataset_config_data.get("parentIdentifier")

        # Extra debugging
        print(f"[DEBUG] parent_object_type from config: {parent_object_type}")
        print(f"[DEBUG] parent_identifier_excel_column from config: {parent_identifier_excel_column}")

        for i, row in df.iterrows():
            # Print de kolomkoppen alleen voor de eerste rij om logs te beperken
            if i == 0:
                print(f"[DEBUG] Excel column headers: {list(row.keys())}")

            attributes = {}
            for excel_col, api_field in self.columns_mapping.items():
                original_value = row[excel_col]
                field_metadata = metadata_map.get(api_field, {})
                new_value = type_mapper.convert_value(original_value, field_metadata)
                attributes[api_field] = new_value

            data_object = {
                "objectType": object_type,
                "identifier": str(row["identifier"]),
                "attributes": attributes
            }

            if parent_object_type and parent_identifier_excel_column:
                if parent_identifier_excel_column in row and pd.notna(row[parent_identifier_excel_column]):
                    parent_identifier_value = row[parent_identifier_excel_column]
                    data_object["parentObjectType"] = parent_object_type
                    data_object["parentIdentifier"] = str(parent_identifier_value)
                else:
                    st.warning(f"De kolom '{parent_identifier_excel_column}' opgegeven als parentIdentifier is niet gevonden of leeg in het Excel-bestand.")

            data_to_send.append(data_object)
        return data_to_send

    def _upload_to_vip(self, object_type: str, data_to_send: List[Dict[str, Any]]) -> None:
        try:

            response = self.dataset_config.api_client.upsert_objects_in_batches(objects_data=data_to_send)
            if response:
                response_objects = response.get("objects", [])
                failed_updates = [obj for obj in response_objects if not obj.get("success")]
                if failed_updates:
                    st.error("❌ Mislukte updates:")
                    for fail in failed_updates:
                        st.write(f"- Object {fail.get('identifier')}: {fail.get('message')}")
                st.success(
                    f"✅ Upload Rapport:\n"
                    f"- Totaal aantal objecten: {len(response_objects)}\n"
                    f"- Succesvol bijgewerkt: {sum(1 for obj in response_objects if obj.get('success'))}\n"
                    f"- Mislukt: {sum(1 for obj in response_objects if not obj.get('success'))}"
                )
        except Exception as e:
            st.error(f"❌ Er is een fout opgetreden: {e}")
            st.write("Debug informatie:")


# ---------------------------------------------------------
# Hoofdklasse die de 5 stappen van de Excel-upload coördineert
# ---------------------------------------------------------
class ExcelUploader:
    """
    Hoofdklasse voor het uploaden van een Excel-bestand.
    Het uploadproces is opgedeeld in 5 stappen:
      1. Upload Excel-bestand
      2. Haal metadata op en bouw mappings
      3. Lees het Excel-bestand in en converteer datumkolommen
      4. Valideer de ingelezen Excel-data
      5. Upload de gevalideerde data naar de API
    """

    def __init__(self, config: Dict[str, Any], dataset_config: DatasetConfig, selected_dataset: str):
        self.config = config
        self.dataset_config = dataset_config
        self.selected_dataset = selected_dataset

    def process_upload(self) -> None:
        # Stap 1: Upload Excel-bestand
        step1 = ExcelUploadStep1()
        excel_file = step1.upload_excel_file()
        if not excel_file:
            return

        # Stap 2: Haal metadata op en bouw mappings
        step2 = ExcelUploadStep2(self.config, self.dataset_config)
        metadata, columns_mapping, dtype_mapping, date_format_mapping = step2.get_metadata_and_mappings()
        if not metadata:
            return

        # Stap 3: Lees het Excel-bestand in en converteer datumkolommen
        step3 = ExcelUploadStep3(dtype_mapping, date_format_mapping)
        df = step3.read_and_convert_excel(excel_file)
        step3.show_preview(df)

        # Stap 4: Valideer de ingelezen Excel-data
        step4 = ExcelUploadStep4(self.config, self.dataset_config, self.selected_dataset, columns_mapping, metadata)
        if not step4.validate_excel(df):
            return

        # Stap 5: Upload de gevalideerde data als de gebruiker op de knop drukt
        if st.button("Upload naar VIP"):
            full_dataset_config = self.dataset_config.get_dataset_config(self.selected_dataset)
            step5 = ExcelUploadStep5(full_dataset_config, self.dataset_config, self.selected_dataset, columns_mapping,
                                     metadata)
            step5.upload_data(df)
