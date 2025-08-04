import io
import logging
import re
from typing import Any, Dict, List, Optional
import pandas as pd
from xlsxwriter.workbook import Workbook
from io import BytesIO

logger = logging.getLogger(__name__)


def sanitize_name(name: str) -> str:
    """
    Converteer een gegeven naam naar een veilige Excel-naam door alle niet-alfanumerieke
    tekens te vervangen met een underscore. Als de naam met een cijfer of underscore begint,
    voeg dan een 'N' toe aan het begin. Excel named ranges mogen bijvoorbeeld niet met
    een cijfer beginnen. Daarnaast wordt de lengte beperkt tot 255 karakters.

    Args:
        name (str): De originele naam die gesaneerd moet worden.

    Returns:
        str: Een gesaneerde naam geschikt als Excel-named range.
    """
    # Verwijder alle niet-alfa-numerieke karakters
    cleaned = re.sub(r'[^A-Za-z0-9]', '_', name)
    # Als de naam met een cijfer of underscore begint, zet er een 'N' voor
    if re.match(r'^[0-9_]', cleaned):
        cleaned = 'N' + cleaned
    # Beperk de lengte tot 255 karakters
    return cleaned[:255]


def set_column_widths(worksheet: Any,
                      df: pd.DataFrame,
                      min_width: int = 8,
                      max_width: int = 50) -> None:
    """
    Stel de kolombreedtes in op basis van de maximale lengte van de kolomnamen en de data erin.

    We lopen door elke kolom in de DataFrame, berekenen de maximale lengte van de header
    en de inhoud, en bepalen zo een geschikte breedte. Deze breedte wordt vervolgens aangepast
    aan minimale en maximale grenzen.

    Args:
        worksheet: De worksheet waarin kolombreedtes moeten worden aangepast.
        df (pd.DataFrame): De DataFrame met de data om breedte op te baseren.
        min_width (int): De minimale kolombreedte.
        max_width (int): De maximale kolombreedte.
    """
    for i, col in enumerate(df.columns):
        # Lengte kolomnaam
        header_length = len(str(col))

        # Lengte van langste waarde in de kolom
        content_length = df[col].astype(str).map(len).max()
        content_length = content_length if not pd.isnull(content_length) else 0

        # Bepaal optimale breedte (neem de grootste van header of content, met marge)
        optimal_width = max(header_length, content_length) + 2

        # Pas min/max constraints toe
        column_width = max(min_width, min(optimal_width, max_width))

        # Stel de kolombreedte in
        worksheet.set_column(i, i, column_width)


class ExcelHandler:
    """
    Deze klasse is verantwoordelijk voor het maken van een Excel-bestand op basis van
    meegeleverde data, metadata, en kolommen-mapping. Het resultaat is een Excel-bestand
    met correcte kolomnamen, validaties, en opmaak.

    Belangrijkste stappen:
    - Data opschonen en in DataFrame laden.
    - Eventuele attributen uitklappen naar losse kolommen.
    - Toevoegen van verplichte kolommen zoals 'objectType' en 'identifier'.
    - Omzetten van interne kolomnamen naar gewenste externe kolomnamen via een mapping.
    - Toepassen van opmaak, validaties en lookup-lijsten in het Excel-bestand.
    """

    def __init__(self,
                 metadata: Dict[str, Any],
                 columns_mapping: Dict[str, str],
                 object_type: str) -> None:
        """
        Initialiseer de ExcelHandler.

        Args:
            metadata (dict): Informatie over elk attribuut, bijvoorbeeld type en opties.
                             Bijvoorbeeld: { internal_key: {"type": "BOOLEAN", ...}, ... }
            columns_mapping (dict): Mapping van Excel kolomnamen naar interne attributen.
                                    Bijvoorbeeld: {"ExterneKolomNaam": "interneAttribuutNaam"}
            object_type (str): De waarde voor de kolom 'objectType' in het Excel-bestand.
        """
        logger.debug("Initialiseren van ExcelHandler...")

        self.metadata = metadata
        self.columns_mapping = columns_mapping

        # Maak inverse mapping aan: interne attribuutnaam -> externe Excel-kolomnaam
        # Dit is handig om later kolommen te hernoemen.
        self.inverse_mapping = {v: k for k, v in columns_mapping.items()}
        self.object_type = object_type
        self.skip_identifier_insert = False

        # De vereiste kolommen: altijd objectType en identifier, plus alle interne attributen
        self.required_columns = ["objectType", "identifier"] + list(columns_mapping.values())

        logger.debug("ExcelHandler geïnitialiseerd.")

    def create_excel_file(self,
                          data: List[Dict[str, Any]],
                          output: Optional[io.BytesIO] = None) -> io.BytesIO:
        """
        Maak een Excel-bestand van de meegeleverde data.

        Deze functie:
        - Controleert of er data is.
        - Zet data om naar een DataFrame.
        - Klapt 'attributes' kolom uit naar losse kolommen (indien aanwezig).
        - Zorgt ervoor dat 'objectType' en 'identifier' aanwezig zijn.
        - Zet boolean waarden om naar 'Ja'/'Nee'.
        - Voegt validaties en opmaak toe aan het Excel-blad.

        Args:
            data (List[Dict[str, Any]]): De data die moet worden geëxporteerd.
                                         Verwacht een lijst van dictionaries.
            output (Optional[io.BytesIO]): Optioneel, een BytesIO object om de Excel in te schrijven.
                                           Als None, wordt een nieuw BytesIO object gemaakt.

        Returns:
            io.BytesIO: Het gegenereerde Excel-bestand in-memory.
        """
        if not data:
            raise ValueError("Geen data om te exporteren")

        if output is None:
            output = io.BytesIO()

        # Debug info over de data
        logger.debug(f"Aantal records in data: {len(data)}")
        logger.debug(f"Type van data: {type(data)}")
        if data:
            logger.debug(f"Eerste object: {data[0]}")

        # Zet data om naar DataFrame
        df = pd.DataFrame(data)

        # Onthoud originele identifier (als die bestaat) voor later herstel
        original_identifier = None
        if 'identifier' in df.columns:
            original_identifier = df['identifier'].copy()

        # Klap eventuele 'attributes' kolom uit naar losse kolommen
        if 'attributes' in df.columns:
            df_attr = df['attributes'].apply(pd.Series)
            df = df.drop(columns=['attributes']).join(df_attr)

        # Voeg objectType kolom toe als die niet bestaat
        if 'objectType' not in df.columns:
            df.insert(0, 'objectType', self.object_type)
        else:
            df['objectType'] = self.object_type

        # Herstel originele identifier of maak een lege aan als die niet bestaat
        if original_identifier is not None:
            df['identifier'] = original_identifier
        elif 'identifier' not in df.columns:
            df.insert(1, 'identifier', [None] * len(df))

        # Clear auto-generated identifiers to prevent duplicates on re-upload
        # These are identified by the pattern: "objectType_shortuuid"
        if 'identifier' in df.columns:
            # Create a mask for identifiers that are strings and match the pattern
            pattern = f"^{self.object_type}_[a-f0-9-]{{8}}$"
            mask = df['identifier'].str.match(pattern, na=False)
            df.loc[mask, 'identifier'] = None

        # Boolean kolommen omzetten naar 'Ja'/'Nee'
        # We zoeken eerst naar alle attributen in metadata met type BOOLEAN
        boolean_keys = [k for k, v in self.metadata.items() if v.get('type') == 'BOOLEAN']
        for key in boolean_keys:
            if key in df.columns:
                # Map 'true' -> 'Ja', 'false' -> 'Nee'
                # na_action='ignore' betekent dat NaN waarden niet worden aangepast.
                df[key] = df[key].map({'true': 'Ja', 'false': 'Nee'}, na_action='ignore')

        # Date kolommen met dateFormat 'yyyy' omzetten naar jaartallen
        date_year_keys = [k for k, v in self.metadata.items() if v.get('type') == 'DATE' and v.get('dateFormat') == 'yyyy']
        for key in date_year_keys:
            if key in df.columns:
                # Create a mask for non-null values
                non_null_mask = df[key].notna()

                # Only process dates where we have actual values
                if non_null_mask.any():
                    # Map '2014-12-31T23:00:00Z' -> '2015'
                    date = pd.to_datetime(df.loc[non_null_mask, key], errors='coerce')
                    # Check of de datum op het einde van het jaar valt om 23:00 (vectorized operation)
                    end_of_year_mask = (date.dt.month == 12) & (date.dt.day == 31) & (date.dt.hour == 23)

                    # Update only the rows with actual dates
                    df.loc[non_null_mask & end_of_year_mask, key] = (date[end_of_year_mask].dt.year + 1).astype(str)
                    df.loc[non_null_mask & ~end_of_year_mask, key] = date[~end_of_year_mask].dt.year.astype(str)

                # Set all remaining null values to empty string
                df[key] = df[key].replace({pd.NA: '', pd.NaT: '', None: '', 'nan': '', float('nan'): ''})

        # Correct general date columns that are not just year
        date_other_keys = [k for k, v in self.metadata.items() if v.get('type') == 'DATE' and v.get('dateFormat') != 'yyyy']
        for key in date_other_keys:
            if key in df.columns:
                # Create a mask for non-null values
                non_null_mask = df[key].notna()

                if non_null_mask.any():
                    # Convert to datetime objects
                    dates = pd.to_datetime(df.loc[non_null_mask, key], errors='coerce')

                    # Identify dates that need a +1 hour adjustment
                    adjustment_mask = dates.dt.strftime('%H:%M:%S') == '23:00:00'
                    
                    # Apply the +1 hour adjustment
                    adjusted_dates = dates[adjustment_mask] + pd.Timedelta(hours=1)
                    
                    # Update DataFrame: apply adjustment and format all dates
                    df.loc[non_null_mask & adjustment_mask, key] = adjusted_dates.dt.strftime('%d-%m-%Y')
                    df.loc[non_null_mask & ~adjustment_mask, key] = dates[~adjustment_mask].dt.strftime('%d-%m-%Y')

                # Ensure NaT values become empty strings
                df[key] = df[key].replace({pd.NaT: ''})

        # Controleer of alle vereiste kolommen bestaan, zo niet, voeg ze toe met None
        for rc in self.required_columns:
            if rc not in df.columns:
                df[rc] = None

        # Verwijder dubbele kolommen (mocht dat om wat voor reden dan ook zijn voorgekomen)
        df = df.loc[:, ~df.columns.duplicated()]

        # Orden de kolommen volgens self.required_columns
        columns_to_use = [col for col in self.required_columns if col in df.columns]
        df = df[columns_to_use]

        # Hernoem interne kolommen naar externe kolomnamen m.b.v. inverse_mapping
        rename_map = {}
        for c in df.columns:
            if c in ["objectType", "identifier"]:
                # Deze kolommen blijven gelijk
                continue
            excel_col = self.inverse_mapping.get(c)
            if excel_col:
                rename_map[c] = excel_col
        df.rename(columns=rename_map, inplace=True)

        # Debug info over het eindresultaat
        logger.debug(f"Finale kolommen in DataFrame: {df.columns.tolist()}")
        if len(df) > 0:
            logger.debug(f"Eerste rij van finale data: {df.iloc[0].to_dict()}")
        else:
            logger.debug("Geen data in de DataFrame na verwerking.")

        # Schrijf DataFrame naar Excel
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Data")

        # Format en style het Excel bestand
        self.format_excel_sheet(
            workbook=writer.book,
            worksheet=writer.sheets["Data"],
            df=df,
            metadata=self.metadata,
            columns_mapping=self.columns_mapping
        )

        # Afronden en terug naar het begin van de BytesIO buffer
        writer.close()
        output.seek(0)
        return output

    def format_excel_sheet(self,
                           workbook: Workbook,
                           worksheet: Any,
                           df: pd.DataFrame,
                           metadata: Dict[str, Any],
                           columns_mapping: Dict[str, str]) -> None:
        """
        Format en style een Excel-werkblad:
        - Voegt header-format toe.
        - Past kolombreedtes aan.
        - Voegt filters, bevroren rijen/kolommen en lookup-lijsten toe.
        - Voegt datavalidatie toe voor boolean, enumeraties en datums.

        Args:
            workbook (Workbook): Het xlsxwriter workbook object.
            worksheet: Het worksheet object waarin opmaak moet worden toegepast.
            df (pd.DataFrame): De DataFrame met einddata.
            metadata (dict): Metadata met informatie over types en opties.
            columns_mapping (dict): Mapping van Excel kolomnamen naar interne attributen.
        """
        # Header opmaak
        header_format = workbook.add_format({
            'bg_color': '#ededed',
            'align': 'left',
            'border': 1
        })

        # Headers stylen
        for col_num, value in enumerate(df.columns):
            worksheet.write(0, col_num, value, header_format)

        # Kolombreedtes instellen
        set_column_widths(worksheet, df)

        # Autofilter en freeze panes
        worksheet.autofilter(0, 0, 0, len(df.columns) - 1)
        worksheet.freeze_panes(1, 2)

        # Maak een lookup sheet voor enumeraties en boolean waardes
        lookup_sheet = workbook.add_worksheet("Lookup_Lists")

        # Boolean opties toevoegen
        boolean_options = ["Ja", "Nee"]
        for i, opt in enumerate(boolean_options):
            lookup_sheet.write(i, 0, opt)
        workbook.define_name("BooleanList", "='Lookup_Lists'!$A$1:$A$2")

        # Inverse mapping voor eenvoudige lookup van interne keys
        inv_map = {ec: ic for ec, ic in columns_mapping.items()}

        # Enumeraties afhandelen (velden met 'attributeValueOptions')
        enum_col = 1
        enum_ranges = {}
        created_named_ranges = set()
        for col_num, excel_col_name in enumerate(df.columns):
            if excel_col_name in ["objectType", "identifier"]:
                continue
            internal_key = inv_map[excel_col_name]
            field_meta = metadata.get(internal_key, {})

            if 'attributeValueOptions' in field_meta:
                # Als dit veld enumeratie-opties heeft, schrijf ze weg en maak een named range
                options = field_meta['attributeValueOptions']
                list_name = sanitize_name(internal_key)
                if list_name not in created_named_ranges and options:
                    for row_i, val in enumerate(options):
                        lookup_sheet.write(row_i, enum_col, val)
                    col_letter = chr(ord('A') + enum_col)
                    workbook.define_name(
                        list_name,
                        f"=Lookup_Lists!${col_letter}$1:${col_letter}${len(options)}"
                    )
                    enum_ranges[internal_key] = list_name
                    enum_col += 1
                    created_named_ranges.add(list_name)

        # Datavalidatie toepassen
        start_row = 1
        end_row = start_row + len(df) - 1

        # Vergrendel de eerste twee kolommen (objectType, identifier) tegen aanpassingen
        # (In dit geval geven we alleen een waarschuwing, het is geen echte "lock")
        for c in range(min(2, df.shape[1])):
            worksheet.data_validation(
                start_row, c, end_row, c,
                {
                    'validate': 'any',
                    'input_title': 'Let op!',
                    'input_message': 'Deze kolom mag niet worden aangepast.',
                    'show_input': True
                }
            )

        # Specifieke validaties per kolom
        for col_num, excel_col_name in enumerate(df.columns):
            if excel_col_name in ["objectType", "identifier"]:
                continue
            internal_key = inv_map[excel_col_name]
            field_meta = metadata.get(internal_key, {})

            # Boolean validatie
            if field_meta.get('type') == 'BOOLEAN':
                worksheet.data_validation(
                    start_row, col_num, end_row, col_num,
                    {
                        "validate": "list",
                        "source": "=BooleanList"
                    }
                )

            # Enumeratie validatie
            if internal_key in enum_ranges:
                worksheet.data_validation(
                    start_row, col_num, end_row, col_num,
                    {
                        "validate": "list",
                        "source": f"={enum_ranges[internal_key]}"
                    }
                )

            # Datumvalidatie, bijvoorbeeld enkel jaartallen tussen 1900 en 2100
            if field_meta.get('type') == 'DATE' and field_meta.get('dateFormat') == 'yyyy':
                worksheet.data_validation(
                    start_row, col_num, end_row, col_num,
                    {
                        'validate': 'integer',
                        'criteria': 'between',
                        'minimum': 1900,
                        'maximum': 2100,
                        'error_message': 'Geef een geldig jaar (1900-2100) op.'
                    }
                )

            # Numerieke validatie, bijvoorbeeld enkel hele getallen
            if field_meta.get('type') == 'INT':
                worksheet.data_validation(
                    start_row, col_num, end_row, col_num,
                    {
                        'validate': 'integer',
                        'criteria': '>=',
                        'value': 0,
                        'error_message': 'Geef een geldig geheel getal op.'
                    }
                )

        # Conditionele opmaak voor boolean velden:
        # Indien een waarde niet 'Ja' of 'Nee' is, geef een gele achtergrond
        worksheet.conditional_format(
            start_row, 0, end_row, len(df.columns)-1,
            {
                'type': 'formula',
                'criteria': '=AND(INDIRECT("R"&ROW()&"C"&COLUMN(),FALSE)<>"Ja",INDIRECT("R"&ROW()&"C"&COLUMN(),FALSE)<>"Nee")',
                'format': workbook.add_format({'bg_color': '#FFFF00'})
            }
        )


def create_excel_download(data: bytes) -> Optional[BytesIO]:
    """
    Maak een in-memory Excel-bestand geschikt voor download.

    Args:
        data (bytes): De bytes die het Excel-bestand voorstellen.

    Returns:
        Optional[BytesIO]: Een BytesIO object met Excel-inhoud of None bij een fout.
    """
    try:
        # Converteer bytes naar BytesIO
        excel_buffer = BytesIO(data)
        return excel_buffer
    except Exception as e:
        print(f"Fout bij het creëren van de Excel download: {e}")
        return None


if __name__ == "__main__":
    # In deze blok kunnen we enkele onafhankelijke functies testen voor debugging.

    # Test sanitize_name
    test_name = "123_Col&Name@!"
    print("Test sanitize_name:", sanitize_name(test_name))

    # Test set_column_widths door een dummy DataFrame te maken en naar Excel te schrijven
    df_test = pd.DataFrame({
        "Kolom1": ["Een", "Twee", "Drie"],
        "Kolom2": ["Dit is een langere waarde", "Kort", "Nog eentje"]
    })
    buffer = BytesIO()
    writer = pd.ExcelWriter(buffer, engine="xlsxwriter")
    df_test.to_excel(writer, index=False, sheet_name="Test")
    set_column_widths(writer.sheets["Test"], df_test)
    writer.close()
    buffer.seek(0)
    print("set_column_widths is uitgevoerd op een test DataFrame.")

    # Test create_excel_download
    dummy_bytes = b"Dummy Excel content"
    result = create_excel_download(dummy_bytes)
    if result is not None:
        print("create_excel_download: Succesvol een BytesIO object gemaakt.")
    else:
        print("create_excel_download: Mislukt om een BytesIO object te maken.")
