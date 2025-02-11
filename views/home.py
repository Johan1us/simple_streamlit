import logging
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# Importeer de benodigde helpers en API-client
from utils.api_client import APIClient
from utils.dataset_config import DatasetConfig
from handlers.excel_uploader import ExcelUploader
from handlers.dataset_downloader import DatasetDownloader


# Stel logging in op DEBUG-niveau voor gedetailleerde informatie
logging.basicConfig(level=logging.DEBUG)

class VIPDataMakelaarApp:
    """
    Hoofdklasse voor de VIP DataMakelaar applicatie.

    De applicatie bestaat uit drie stappen:
      1. Dataset selecteren
      2. Excel downloaden (genereren)
      3. Excel uploaden
    """

    def __init__(self):
        # Haal API-gegevens op uit de omgevingsvariabelen
        client_id = os.getenv("LUXS_PROD_CLIENT_ID")
        client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET")
        base_url = os.getenv("LUXS_PROD_BASE_URL")
        token_url = os.getenv("LUXS_PROD_TOKEN_URL")

        self.api_client = APIClient(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            token_url=token_url
        )

        # Bepaal het projectpad en initialiseer de DatasetConfig
        huidige_map = Path(__file__).resolve().parent
        project_root = huidige_map.parent
        self.dataset_manager = DatasetConfig(project_root, self.api_client)

    def start(self) -> None:
        """
        Voer de applicatie uit met de drie hoofdstappen.
        """
        titel_kolom = self._toon_uitlog_knop()
        with titel_kolom:
            st.title("VIP DataMakelaar")

        st.header("Stap 1: Selecteer een dataset")
        geselecteerde_dataset = self._selecteer_dataset()

        if geselecteerde_dataset and geselecteerde_dataset != "Selecteer dataset":
            dataset_configuratie = self.dataset_manager.get_dataset_config(geselecteerde_dataset)
            self._toon_dataset_velden(dataset_configuratie)
            print("toon dataset velden")

            # check if complexFilter is true
            complex_filter = dataset_configuratie.get("complexFilter", False)
            if complex_filter:
                complexen = self.get_complexen()

                complex_selectie = self.toon_complexen(complexen=complexen)
            else:
                complex_selectie = None
                complex_filter = True
            if dataset_configuratie and complex_filter:

                st.header("Stap 2: Download Excel")
                self._stap_download_excel(geselecteerde_dataset, dataset_configuratie, complex_selectie)
                st.header("Stap 3: Upload Excel")
                self._stap_upload_excel(geselecteerde_dataset, dataset_configuratie)

    def _toon_uitlog_knop(self):
        """
        Toon een uitlog-knop in een aparte kolom.
        """
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("Uitloggen", key="logout_btn"):
                st.session_state["logged_in"] = False
                st.rerun()
        return col1

    def _selecteer_dataset(self) -> str:
        """
        Laat de gebruiker een dataset kiezen via een dropdown-menu.
        """
        datasets = self.dataset_manager.get_available_datasets()
        opties = ["Selecteer dataset"] + datasets
        return st.selectbox("Dataset", opties, index=0)

    def _toon_dataset_velden(self, config: dict) -> None:
        """
        Toon de Excel-kolomnamen (velden) van de geselecteerde dataset.
        """
        excel_columns = [attribuut["excelColumnName"] for attribuut in config.get("attributes", [])]
        df = pd.DataFrame(excel_columns, columns=["Velden :"])
        st.dataframe(df, hide_index=True)

    def _stap_download_excel(self, selected_dataset: str, config: dict, complex_selectie: list = None) -> None:
        """
        Voer stap 2 uit: genereer en bied een Excel-bestand aan voor download.
        """
        
        if st.button("Genereer Excel"):
            downloader = DatasetDownloader(config, self.api_client, complex_selectie=complex_selectie)


            excel_file = downloader.generate_excel()
            file_name = self.dataset_manager.get_file_name(selected_dataset) or "download"
            st.download_button(
                label="Download Excel",
                data=excel_file,
                file_name=f"{file_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    def _stap_upload_excel(self, selected_dataset: str, config: dict) -> None:
        """
        Voer stap 3 uit: verwerk de upload van een Excel-bestand.
        """
        uploader = ExcelUploader(config, self.dataset_manager, selected_dataset)

        # @st.cache_data(ttl=3600)  # Cache for 1 hour
        uploader.process_upload()

    @staticmethod
    def toon_complexen(complexen: list) -> list:
        """
        Toon de complexen die beschikbaar zijn.
        """
        st.write("Selecteer complex:")
        print("Selecteer complex:")
        if complexen:
            df = pd.DataFrame(complexen, columns=["Complexen"])
            df["Selecteer"] = False
            complex_keuze = st.data_editor(df, hide_index=True, use_container_width=True, height=200, column_config={
                "Complexen": "Complex",
                "Selecteer": st.column_config.CheckboxColumn(
                    "Selectie",
                    help="Selecteer de complexen voor deze dataset",
                )
            }, disabled=["Complexen"])
            print(complex_keuze)
            complex_keuze_lijst = []
            for index, row in complex_keuze.iterrows():
                if row["Selecteer"]:
                    complex_keuze_lijst.append(row["Complexen"])


            st.write(f"Je hebt {len(complex_keuze_lijst)} complexen geselecteerd.")
            if len(complex_keuze_lijst) == 1:
                st.write(f"Je hebt {len(complex_keuze_lijst)} complex geselecteerd.")
            else:
                st.write(f"Je hebt {len(complex_keuze_lijst)} complexen geselecteerd.")

            # complex_keuze = st.selectbox("Complex", complex_opties, index=0)
            return complex_keuze_lijst
        return None

    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_complexen(_self):
        """
        Haal de lijst van complexen op uit de API.
        """
        complexen = _self.api_client.get_complexen()
        return complexen


