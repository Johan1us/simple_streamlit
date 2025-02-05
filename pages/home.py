import logging
from pathlib import Path
import os
import pandas as pd
import streamlit as st

# Importeer hulpmiddelen voor datasetbeheer en Excel-verwerking
from utils.dataset_manager import DatasetManager
from utils.excel_upload import handle_excel_upload
from utils.excel_download import handle_excel_download
from utils.api_client import APIClient

# Stel logging in op DEBUG-niveau voor gedetailleerde informatie (voor ontwikkelaars)
logging.basicConfig(level=logging.DEBUG)


def toon_uitlog_knop() -> None:
    """
    Toon de uitlog-knop in de rechterkolom en handel de uitlogactie af.
    Als er op de knop gedrukt wordt, wordt de 'logged_in'-status op False gezet en de app herstart.
    """
    # Maak twee kolommen: een voor de titel (breedte 6) en één voor de uitlogknop (breedte 1)
    col1, col2 = st.columns([6, 1])
    with col2:
        # Toon de uitlog-knop en controleer of erop gedrukt wordt
        if st.button("Uitloggen", key="logout_btn"):
            st.session_state["logged_in"] = False
            st.rerun()  # Herstart de app om de uitlogactie door te voeren
    return col1


def selecteer_dataset(dataset_manager: DatasetManager) -> str:
    """
    Laat de gebruiker een dataset selecteren uit de beschikbare opties.

    Args:
        dataset_manager (DatasetManager): De manager die beschikbare datasets beheert.

    Returns:
        str: De naam van de geselecteerde dataset.
    """
    # Verkrijg de lijst met beschikbare datasets
    datasets = dataset_manager.get_available_datasets()
    # Voeg een standaard optie toe aan de lijst
    opties = ["Selecteer dataset"] + datasets
    # Toon een dropdown-menu voor datasetselectie
    selected_dataset = st.selectbox("Dataset", opties, index=0)
    return selected_dataset


def toon_dataset_velden(config: dict) -> None:
    """
    Toon de velden (Excel kolomnamen) van de geselecteerde dataset in een tabel.

    Args:
        config (dict): Configuratie van de geselecteerde dataset.
    """
    # Haal de Excel-kolomnamen op uit de attributen van de configuratie
    excel_columns = [attribuut["excelColumnName"] for attribuut in config.get("attributes", [])]
    # Maak een DataFrame met de kolomnamen zodat deze netjes getoond kunnen worden
    df = pd.DataFrame(excel_columns, columns=["Velden :"])
    st.dataframe(df, hide_index=True)


def genereer_en_download_excel(selected_dataset: str, config: dict, dataset_manager: DatasetManager) -> None:
    """
    Genereer een Excel-bestand op basis van de datasetconfiguratie en bied deze aan voor download.

    Args:
        selected_dataset (str): Naam van de geselecteerde dataset.
        config (dict): Configuratie van de dataset.
        dataset_manager (DatasetManager): Manager voor datasetbeheer.
    """
    # Haal de bestandsnaam op voor de download; gebruik 'download' als fallback
    file_name = dataset_manager.get_file_name(selected_dataset) or "download"
    st.write(f"Excel voor {selected_dataset} wordt gegenereerd...")
    try:
        # Genereer het Excel-bestand met de opgegeven configuratie en API-client
        excel_file = handle_excel_download(config, dataset_manager.api_client)
        # Toon een download-knop voor het gegenereerde Excel-bestand
        st.download_button(
            label="Download Excel",
            data=excel_file,
            file_name=f"{file_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        # Als er een fout optreedt, geef dan een foutmelding met technische details
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
        st.info(
            "💡 Suggestie: Controleer of alle benodigde configuraties correct zijn en of er verbinding is met de API.")


def show_home() -> None:
    """
    Hoofdfunctie voor de Streamlit-pagina.

    Deze functie zorgt voor de volgende stappen:
      1. Dataset selectie.
      2. Downloaden van een Excel-bestand op basis van de dataset.
      3. Uploaden van een Excel-bestand.
    """
    client_id = os.getenv("LUXS_PROD_CLIENT_ID")
    client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET")
    base_url = os.getenv("LUXS_PROD_BASE_URL")
    token_url = os.getenv("LUXS_PROD_TOKEN_URL")

    api_client = APIClient(client_id=client_id, client_secret=client_secret, base_url=base_url, token_url=token_url)

    # Toon de uitlog-knop en verkrijg de kolom waar de titel in komt
    titel_kolom = toon_uitlog_knop()
    with titel_kolom:
        # Toon de titel van de applicatie
        st.title("VIP DataMakelaar")

    # Stap 1: Selecteer een dataset
    st.header("Stap 1: Selecteer een dataset")

    # Bepaal het pad naar de projectroot; __file__ geeft het huidige bestandspad
    huidige_map = Path(__file__).resolve().parent
    project_root = huidige_map.parent
    # Initialiseer de DatasetManager met het pad naar de projectroot
    dataset_manager = DatasetManager(project_root)
    # Laat de gebruiker een dataset selecteren
    selected_dataset = selecteer_dataset(dataset_manager)

    # Controleer of een geldige dataset is geselecteerd (anders blijft de standaardwaarde staan)
    if selected_dataset and selected_dataset != "Selecteer dataset":
        # Haal de configuratie op voor de geselecteerde dataset
        config = dataset_manager.get_dataset_config(selected_dataset)
        if config:
            # Toon de velden (Excel kolomnamen) van de dataset
            toon_dataset_velden(config)

            # Stap 2: Download Excel
            st.header("Stap 2: Download Excel")
            # Als op de knop "Geneer Excel" gedrukt wordt, genereer en download het Excel-bestand
            if st.button("Geneer Excel"):
                genereer_en_download_excel(selected_dataset, config, dataset_manager)

            # Stap 3: Upload Excel
            st.header("Stap 3: Upload Excel")
            # Handel de upload van een Excel-bestand af met de gegeven configuratie
            handle_excel_upload(config, dataset_manager, selected_dataset)
