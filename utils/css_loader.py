import os
import logging
import streamlit as st


# Stel logging in op DEBUG-niveau voor extra informatie (voor ontwikkelaars)
logging.basicConfig(level=logging.INFO)


def load_css(current_dir):
    """
    Laad het CSS-bestand voor de styling van de webapp.
    Als het bestand niet gevonden wordt of er een fout optreedt bij het lezen,
    wordt er fallback CSS toegepast en wordt extra informatie getoond om te helpen bij het debuggen.
    """
    # Bepaal de huidige directory en het pad naar het CSS-bestand

    css_path = os.path.join(current_dir, "assets", "css", "style.css")

    # Controleer of het CSS-bestand bestaat
    if os.path.exists(css_path):
        try:
            # Lees het CSS-bestand in
            with open(css_path, 'r', encoding='utf-8') as file:
                css_content = file.read()
            # Pas de CSS styling toe in de Streamlit app
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
            logging.debug("CSS is succesvol geladen en toegepast.")
        except Exception as error:
            # Toon een foutmelding als er een probleem is bij het lezen van het bestand
            st.error(f"Fout bij het lezen van het CSS-bestand: {error}")
            logging.error(f"CSS leesfout: {error}", exc_info=True)
    else:
        # Als het CSS-bestand niet gevonden is, toon een foutmelding en de directorystructuur
        st.error(f"CSS-bestand niet gevonden op: {css_path}")

        # Pas fallback CSS styling toe zodat de app er toch redelijk uitziet
        st.warning("Fallback CSS styling wordt toegepast...")
        st.markdown("""
            <style>
                .stButton > button {
                    background-color: #0066cc;
                    color: white;
                    border-radius: 4px;
                    padding: 0.5rem 1rem;
                    border: none;
                }
                .stButton > button:hover {
                    background-color: #0052a3;
                }
            </style>
        """, unsafe_allow_html=True)

