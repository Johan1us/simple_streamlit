from typing import Dict, List, Tuple, Union, Any
import pandas as pd

class ExcelValidator:
    def __init__(self, metadata: dict, columns_mapping: dict, object_type: str):
        self.metadata = metadata
        self.columns_mapping = columns_mapping
        self.reverse_mapping = {v: k for k, v in columns_mapping.items()}
        self.object_type = object_type

    def validate_excel(self, df: pd.DataFrame) -> List[Dict]:
        """
        Valideer een Excel bestand tegen de metadata specificaties.

        Args:
            df (pd.DataFrame): Het DataFrame met de Excel data

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        self._print_validation_header()

        # Kolommen validatie
        excel_columns, config_columns = self._get_column_sets(df)
        errors.extend(self._validate_columns(df, excel_columns, config_columns))

        # Data validatie
        errors.extend(self._validate_data_in_columns(df))

        # ObjectType validatie
        errors.extend(self._validate_object_type(df, excel_columns))

        # Print resultaten
        self._print_validation_results(errors)

        return errors

    def _print_validation_header(self):
        print("\n### Validatie Resultaten ###")

    def _get_column_sets(self, df: pd.DataFrame) -> Tuple[set, set]:
        excel_columns = set(df.columns)
        config_columns = set(self.reverse_mapping.values())
        config_columns.update({"objectType", "identifier"})
        return excel_columns, config_columns

    def _validate_columns(self, df: pd.DataFrame, excel_columns: set, config_columns: set) -> List[Dict]:
        errors = []

        # Basis kolommen analyse
        self._print_column_analysis(excel_columns, config_columns)

        # Valideer verplichte systeem kolommen
        errors.extend(self._validate_required_columns(df, excel_columns))

        # Valideer ontbrekende en extra kolommen
        errors.extend(self._validate_missing_columns(excel_columns, config_columns))
        errors.extend(self._validate_extra_columns(excel_columns, config_columns))

        return errors

    def _validate_data_in_columns(self, df: pd.DataFrame) -> List[Dict]:
        errors = []
        for api_name, excel_name in self.reverse_mapping.items():
            if excel_name not in df.columns:
                errors.append(self._create_error("N/A", excel_name,
                    "Verplichte kolom ontbreekt", "Kolom ontbreekt", "Kolom aanwezig"))
                continue

            field_metadata = self.metadata.get(api_name, {})
            errors.extend(self._validate_column_data(df, excel_name, field_metadata))

        return errors

    def _validate_column_data(self, df: pd.DataFrame, excel_name: str, field_metadata: Dict) -> List[Dict]:
        errors = []
        for idx, value in df[excel_name].items():
            row_num = idx + 2

            # Validaties voor lege waarden
            if pd.isna(value):
                if field_metadata.get("required", False):
                    errors.append(self._create_error(row_num, excel_name,
                        "Verplicht veld mag niet leeg zijn", "Leeg", "Niet leeg"))
                continue

            # Type validatie
            errors.extend(self._validate_value_type(row_num, excel_name, value, field_metadata))

            # Format validatie
            errors.extend(self._validate_value_format(row_num, excel_name, value, field_metadata))

            # Toegestane waarden validatie
            errors.extend(self._validate_allowed_values(row_num, excel_name, value, field_metadata))

        return errors

    def _create_error(self, row: Union[int, str], column: str, error: str,
                     found: str, expected: str) -> Dict:
        return {
            "row": row,
            "column": column,
            "error": error,
            "found": found,
            "expected": expected
        }

    def _validate_value_type(self, row: int, column: str, value: Any,
                           metadata: Dict) -> List[Dict]:
        errors = []
        if "type" not in metadata:
            return errors

        type_value = metadata["type"].upper()

        # Converteer integers naar strings als STRING verwacht wordt
        if type_value == "STRING" and isinstance(value, (int, float)):
            value = str(value)

        type_validators = {
            "STRING": lambda v: isinstance(v, str),
            "NUMBER": lambda v: self._is_number(v),
            "BOOLEAN": lambda v: str(v).lower() in ["ja", "nee", None],
            "DATE": lambda v: self._is_valid_date(v)
        }

        if type_value in type_validators and not type_validators[type_value](value):
            error_messages = {
                "STRING": ("Waarde moet een tekst zijn", "string"),
                "NUMBER": ("Waarde moet een getal zijn", "getal"),
                "BOOLEAN": ("Waarde moet Ja, Nee of leeg zijn", "Ja, Nee of leeg"),
                "DATE": ("Waarde moet een geldige datum zijn", "datum (bijv. 01-01-2023)")
            }
            msg, expected = error_messages[type_value]
            errors.append(self._create_error(row, column, msg, str(value), expected))

        return errors

    @staticmethod
    def _is_number(value: Any) -> bool:
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_valid_date(value: Any) -> bool:
        try:
            pd.to_datetime(value)
            return True
        except (ValueError, TypeError):
            return False

    def _print_validation_results(self, errors: List[Dict]):
        if errors:
            print(f"\nAantal gevonden fouten: {len(errors)}")
            for error in errors:
                print(f"Rij {error['row']}, Kolom '{error['column']}': {error['error']}")
                print(f"  Gevonden: {error['found']}")
                print(f"  Verwacht: {error['expected']}")
        else:
            print("\nGeen validatiefouten gevonden!")

    def _print_column_analysis(self, excel_columns: set, config_columns: set):
        """
        Print een analyse van de kolommen in het Excel bestand.

        Args:
            excel_columns (set): Set van kolommen in het Excel bestand
            config_columns (set): Set van kolommen in de configuratie
        """
        print("\nKolommenanalyse:")
        print(f"Aantal kolommen in Excel: {len(excel_columns)}")
        print(f"Aantal kolommen in configuratie: {len(config_columns)}")

        missing_columns = config_columns - excel_columns
        extra_columns = excel_columns - config_columns

        if missing_columns:
            print("\nOntbrekende kolommen:")
            for col in missing_columns:
                print(f"- {col}")

        if extra_columns:
            print("\nExtra kolommen in Excel (niet in configuratie):")
            for col in extra_columns:
                print(f"- {col}")

        print("\nAanwezige kolommen:")
        for col in sorted(excel_columns & config_columns):
            print(f"- {col}")

    def _validate_required_columns(self, df: pd.DataFrame, excel_columns: set) -> List[Dict]:
        """
        Valideer de aanwezigheid en inhoud van verplichte systeem kolommen.

        Args:
            df (pd.DataFrame): Het DataFrame met de Excel data
            excel_columns (set): Set van kolommen in het Excel bestand

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        required_columns = ['identifier']

        for col in required_columns:
            if col not in excel_columns:
                errors.append(self._create_error(
                    "N/A",
                    col,
                    "Verplichte systeemkolom ontbreekt",
                    "Kolom ontbreekt",
                    "Kolom moet aanwezig zijn"
                ))
            else:
                # Controleer of er lege waarden zijn in deze kolommen
                empty_rows = df[df[col].isna()].index + 2  # +2 voor Excel rijnummering
                for row in empty_rows:
                    errors.append(self._create_error(
                        row,
                        col,
                        "Verplichte systeemkolom mag niet leeg zijn",
                        "Lege waarde",
                        "Niet-lege waarde"
                    ))

        return errors

    def _validate_missing_columns(self, excel_columns: set, config_columns: set) -> List[Dict]:
        """
        Valideer welke verplichte kolommen ontbreken in het Excel bestand.

        Args:
            excel_columns (set): Set van kolommen in het Excel bestand
            config_columns (set): Set van kolommen in de configuratie

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        missing_columns = config_columns - excel_columns

        for col in missing_columns:
            # Controleer of de kolom verplicht is volgens de metadata
            if any(self.metadata.get(api_name, {}).get("required", False)
                  for api_name, excel_name in self.reverse_mapping.items()
                  if excel_name == col):
                errors.append(self._create_error(
                    "N/A",
                    col,
                    "Verplichte kolom ontbreekt",
                    "Kolom ontbreekt",
                    "Kolom moet aanwezig zijn"
                ))

        return errors

    def _validate_extra_columns(self, excel_columns: set, config_columns: set) -> List[Dict]:
        """
        Valideer welke extra kolommen aanwezig zijn in het Excel bestand.

        Args:
            excel_columns (set): Set van kolommen in het Excel bestand
            config_columns (set): Set van kolommen in de configuratie

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        extra_columns = excel_columns - config_columns

        for col in extra_columns:
            errors.append(self._create_error(
                "N/A",
                col,
                "Onbekende kolom aanwezig",
                "Extra kolom",
                "Kolom niet gedefinieerd in configuratie"
            ))

        return errors

    def _validate_value_format(self, row: int, column: str, value: Any, metadata: Dict) -> List[Dict]:
        """
        Valideer het format van een waarde volgens de metadata specificaties.

        Args:
            row (int): Rijnummer
            column (str): Kolomnaam
            value (Any): De te valideren waarde
            metadata (Dict): Metadata specificaties

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        if "dataFormat" not in metadata:
            return errors

        data_format = metadata["dataFormat"]
        if data_format == "yyyy":
            try:
                year = int(str(value))
                if not (1900 <= year <= 2100):  # redelijke jaar range
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(self._create_error(
                    row,
                    column,
                    "Waarde moet een geldig jaartal zijn",
                    str(value),
                    "jaartal tussen 1900-2100"
                ))

        return errors

    def _validate_allowed_values(self, row: int, column: str, value: Any, metadata: Dict) -> List[Dict]:
        """
        Valideer of een waarde voorkomt in de lijst met toegestane waarden.

        Args:
            row (int): Rijnummer
            column (str): Kolomnaam
            value (Any): De te valideren waarde
            metadata (Dict): Metadata specificaties

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []
        if "attributeValueOptions" not in metadata or not metadata["attributeValueOptions"]:
            return errors

        allowed_values = metadata["attributeValueOptions"]
        if str(value) not in allowed_values:
            errors.append(self._create_error(
                row,
                column,
                "Waarde moet één van de toegestane opties zijn",
                str(value),
                f"één van: {', '.join(allowed_values)}"
            ))

        return errors

    def _validate_object_type(self, df: pd.DataFrame, excel_columns: set) -> List[Dict]:
        """
        Valideer het objectType in het Excel bestand.

        Args:
            df (pd.DataFrame): Het DataFrame met de Excel data
            excel_columns (set): Set van kolommen in het Excel bestand

        Returns:
            List[Dict]: Lijst met gevonden fouten
        """
        errors = []

        if 'objectType' not in excel_columns:
            errors.append(self._create_error(
                "N/A",
                "objectType",
                "Verplichte systeemkolom ontbreekt",
                "Kolom ontbreekt",
                "Kolom moet aanwezig zijn"
            ))
            return errors

        # Controleer lege waarden en correcte objectType
        incorrect_types = df[
            (df['objectType'].isna()) |
            (df['objectType'].fillna('').str.strip() != self.object_type)
        ].index + 2

        for row in incorrect_types:
            found_value = str(df.loc[row-2, 'objectType'])
            if pd.isna(df.loc[row-2, 'objectType']):
                error_msg = "Verplichte systeemkolom mag niet leeg zijn"
                found_value = "Lege waarde"
                expected = "Niet-lege waarde"
            else:
                error_msg = "ObjectType komt niet overeen met configuratie"
                expected = self.object_type

            errors.append(self._create_error(
                row,
                "objectType",
                error_msg,
                found_value,
                expected
            ))

        return errors

if __name__ == "__main__":
    # laad de excel output
    df = pd.read_excel("output.xlsx")
    dataset_name = "PO Daken"
    from VIP_DataMakelaar.app.main import DatasetManager
    config_folder = "config"
    dataset_manager = DatasetManager(config_folder)

    # haal de metadata op voor het objectType
    object_type = dataset_manager.get_object_type(dataset_name)
    metadata = dataset_manager.api_client.get_metadata(object_type)
