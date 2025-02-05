import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.dataset_manager import DatasetManager
from utils.excel_upload import handle_excel_upload
from utils.excel_download import handle_excel_download

logging.basicConfig(level=logging.DEBUG)




def show_home() -> None:
    """Main function for the Streamlit page."""
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Uitloggen", key="logout_btn"):
            st.session_state["logged_in"] = False
            st.rerun()  # Use rerun for restarting the app.

    with col1:
        st.title("VIP DataMakelaar")

    st.header("Stap 1: Selecteer een dataset")

    # Initialize and ensure the configuration folder exists.
    file_folder = Path(__file__).resolve().parent
    project_root = file_folder.parent
    dataset_manager = DatasetManager(project_root)
    datasets =  dataset_manager.get_available_datasets()
    selected_dataset = st.selectbox("Dataset", ["Selecteer dataset"] + datasets, index=0)

    if selected_dataset and selected_dataset != "Geen dataset geselecteerd":
        config = dataset_manager.get_dataset_config(selected_dataset)
        if config:
            excel_columns = [attr["excelColumnName"] for attr in config.get("attributes", [])]
            df = pd.DataFrame(excel_columns, columns=["Velden :"])
            st.dataframe(df, hide_index=True)

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
