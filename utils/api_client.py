import os
import json
import time
import requests
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

# Laad omgevingsvariabelen uit een .env-bestand (als dat aanwezig is)
load_dotenv()


class APIClient:
    """
    Deze klasse verzorgt de communicatie met de Luxs Insights API via OAuth2.

    Belangrijkste functionaliteiten:
      - Automatisch ophalen en vernieuwen van OAuth2 tokens.
      - Ophalen van metadata en objectgegevens.
      - Upsert (toevoegen of bijwerken) en update van objecten.
    """

    def __init__(self, client_id: str, client_secret: str,
                 base_url: str, token_url: str) -> None:
        """
        Initialiseer de APIClient met de benodigde client credentials en basis-URL.

        Args:
            client_id (str): De Client ID voor authenticatie.
            client_secret (str): De Client Secret voor authenticatie.
            base_url (str): De basis-URL van de API.
                            Standaard: "https://api.accept.luxsinsights.com"
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.token_url = token_url
        self.token: Optional[str] = None
        self.token_expires_at: float = 0.0  # Unix-timestamp waarop het token verloopt

    def _get_token(self) -> None:
        """
        Haal een nieuw OAuth2-token op via de client credentials.

        Deze methode verstuurt een POST-verzoek naar de token endpoint en slaat
        het verkregen access token en de vervaltijd op.
        """
        # Gebruik de productie endpoint voor het ophalen van het token
        token_url = self.token_url


        print(f"DEBUG: token_url: {token_url}")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()  # Gooi een error als de statuscode niet 200 is

        token_data = response.json()
        self.token = token_data["access_token"]
        # 'expires_in' geeft de geldigheidsduur in seconden; gebruik 3600 als standaard
        expires_in = token_data.get("expires_in", 3600)
        self.token_expires_at = time.time() + expires_in

    def _ensure_token(self) -> None:
        """
        Zorg ervoor dat er een geldig token beschikbaar is.

        Als het huidige token niet bestaat of verlopen is, wordt er een nieuw token opgehaald.
        """
        if self.token is None or time.time() > self.token_expires_at:
            self._get_token()

    def _headers(self) -> Dict[str, str]:
        """
        Bouw de HTTP-headers voor een API-request, inclusief de Authorization header.

        Returns:
            Dict[str, str]: Een dictionary met de benodigde HTTP-headers.
        """
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_client(self) -> Dict[str, str]:
        """
        Test of de client_id en client_secret correct zijn door geldige headers te retourneren.

        Returns:
            Dict[str, str]: De headers met een geldig OAuth2-token.
        """
        self._ensure_token()
        return self._headers()

    def get_metadata(self, object_type: Optional[str] = None) -> Any:
        """
        Haal metadata op van alle objecttypes, of filter op een specifiek objecttype.

        Args:
            object_type (Optional[str]): (Optioneel) Specifiek objecttype waarvan metadata wordt opgehaald.

        Returns:
            Any: De JSON-respons met de metadata.
        """
        url = f"{self.base_url}v1/metadata"
        params: Dict[str, str] = {}
        if object_type:
            params["objectType"] = object_type

        try:
            response = requests.get(url, headers=self._headers(), params=params)

            # Als er een 500-error optreedt en er is een objectType meegegeven, probeer dan opnieuw zonder filter
            if response.status_code == 500 and object_type:
                print("[DEBUG] 500 error ontvangen, opnieuw proberen zonder objectType parameter...")
                response = requests.get(url, headers=self._headers())
                print(f"[DEBUG] Tweede poging status code: {response.status_code}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request mislukt: {str(e)}")
            print(f"[ERROR] URL geprobeerd: {url}")
            print(f"[ERROR] Verzonden headers: {self._headers()}")
            raise

    def get_objects(
            self,
            object_type: str,
            attributes: Optional[List[str]] = None,
            identifier: Optional[str] = None,
            only_active: bool = False,
            page: int = 0,
            page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Haal een pagina objecten op van een bepaald objecttype.

        Args:
            object_type (str): Het type object dat moet worden opgehaald.
            attributes (Optional[List[str]]): Specifieke attributen om op te halen.
            identifier (Optional[str]): Filter op een specifieke identifier.
            only_active (bool): Alleen actieve objecten ophalen.
            page (int): Paginanummer.
            page_size (int): Aantal objecten per pagina.

        Returns:
            Dict[str, Any]: De JSON-respons van de API met objecten.
        """
        url = f"{self.base_url}/v1/objects/filterByObjectType"
        params: Dict[str, Union[str, int, bool, List[str]]] = {
            "objectType": object_type,
            "onlyActive": str(only_active).lower(),  # De API verwacht 'true' of 'false' als string
            "page": page,
            "pageSize": page_size
        }
        if attributes:
            params["attributes"] = attributes
        if identifier:
            params["identifier"] = identifier

        print(f"[DEBUG] Ophalen objecten van type '{object_type}'")
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] Headers: {self._headers()}")
        print(f"[DEBUG] Params: {params}")

        response = requests.get(url, headers=self._headers(), params=params)
        response.raise_for_status()

        data = response.json()
        # Indien de API een lijst teruggeeft, wrapper deze dan in een dict
        if isinstance(data, list):
            return {
                "objects": data,
                "totalCount": len(data),
                "totalPages": 1,
                "currentPage": 1
            }
        return data

    def get_all_objects(
            self,
            object_type: str,
            attributes: Optional[List[str]] = None,
            identifier: Optional[str] = None,
            only_active: bool = False,
            page_size: int = 1000,
            st=None,
    ) -> Dict[str, Any]:
        """
        Haal alle objecten op van een bepaald objecttype over alle beschikbare pagina's heen.

        Deze methode:
          1. Haalt de eerste pagina op.
          2. Blijft pagina's ophalen totdat er minder objecten dan 'page_size' worden teruggegeven.
          3. Combineert alle objecten in één resultaat.

        Args:
            object_type (str): Het type object dat moet worden opgehaald.
            attributes (Optional[List[str]]): Specifieke attributen om op te halen.
            identifier (Optional[str]): Filter op een specifieke identifier.
            only_active (bool): Alleen actieve objecten ophalen.
            page_size (int): Aantal objecten per pagina.
            st: (Optioneel) Streamlit module voor visuele feedback.

        Returns:
            Dict[str, Any]: Een dictionary met:
                            - "objects": de gecombineerde lijst van objecten,
                            - "totalCount": het totaal aantal objecten,
                            - "pageSize": de gebruikte page_size.
        """
        # Indien st (Streamlit) is meegegeven, maak dan lege feedback-elementen
        status_objects = st.empty() if st is not None else None
        status_totals = st.empty() if st is not None else None
        status_time = st.empty() if st is not None else None

        def feedback():
            if st is not None:
                status_objects.info(f"Batch {current_page + 1} met {len(current_page_objects)} objecten opgehaald")
                status_totals.info(f"Totaal aantal objecten nu: {len(all_objects)}")
                status_time.info(f"Ophalen duurde in totaal {time.time() - start_time:.2f} seconden")

        start_time = time.time()
        all_objects = []
        current_page = 0

        while True:
            # Haal een pagina objecten op
            resp = self.get_objects(
                object_type=object_type,
                attributes=attributes,
                identifier=identifier,
                only_active=only_active,
                page=current_page,
                page_size=page_size
            )

            current_page_objects = resp.get("objects", [])
            all_objects.extend(current_page_objects)
            print(f"[DEBUG] Ophalen duurde {time.time() - start_time:.2f} seconden")
            print(f"[DEBUG] Ophalen pagina {current_page}, {len(current_page_objects)} objecten")
            print(f"[DEBUG] Totaal aantal objecten nu: {len(all_objects)}")
            feedback()

            # Als er minder objecten zijn opgehaald dan 'page_size', is dit de laatste pagina
            if len(current_page_objects) < page_size:
                break

            current_page += 1

        print(f"[DEBUG] Ophalen van alle objecten duurde {time.time() - start_time:.2f} seconden")
        return {
            "objects": all_objects,
            "totalCount": len(all_objects),
            "pageSize": page_size
        }

    def upsert_objects(self, objects_data: List[Dict[str, Any]]) -> Any:
        """
        Voeg nieuwe objecten toe of werk bestaande objecten bij via een POST-request.

        Args:
            objects_data (List[Dict[str, Any]]): Lijst met objectdefinities om toe te voegen of bij te werken.

        Returns:
            Any: De JSON-respons van de API.
        """
        url = f"{self.base_url}/v1/objects"
        print(f"[DEBUG] Upsert van objecten naar {url}")
        response = requests.post(url, headers=self._headers(), json=objects_data)
        response.raise_for_status()
        return response.json()

    def update_objects(self,
                       objects_data: List[Dict[str, Any]],
                       batch_size: int = 100,
                       timeout: int = 300,
                       max_retries: int = 3) -> Any:
        """
        Update bestaande objecten in batches om timeouts te voorkomen via een PUT-request.

        Args:
            objects_data (List[Dict[str, Any]]): Lijst met objectdefinities om bij te werken.
            batch_size (int): Aantal objecten per batch (standaard 100).
            timeout (int): Timeout in seconden per request (standaard 300).
            max_retries (int): Maximaal aantal pogingen per batch (standaard 3).

        Returns:
            Dict[str, Any]: Een dictionary met de gecombineerde resultaten van alle batches.
        """
        url = f"{self.base_url}/v1/objects"
        response_json_list = []

        print(f"[DEBUG] Start update van {len(objects_data)} objecten in batches van {batch_size}")
        print(f"[DEBUG] Timeout per request: {timeout} seconden")


        # Verwerk de objecten in batches met retry-logica
        for i in range(0, len(objects_data), batch_size):
            batch = objects_data[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(objects_data) + batch_size - 1) // batch_size  # Correcte berekening

            for retry in range(max_retries):
                try:
                    print(f"[DEBUG] Verwerken batch {batch_num}/{total_batches} (poging {retry + 1}/{max_retries})")
                    response = requests.put(
                        url,
                        headers=self._headers(),
                        json=batch,
                        timeout=timeout
                    )
                    response.raise_for_status()

                    resp_json = response.json()
                    if isinstance(resp_json, list):
                        response_json_list.extend(resp_json)
                    else:
                        response_json_list.append(resp_json)

                    print(f"[DEBUG] Batch {batch_num} succesvol verwerkt: {len(batch)} objecten")
                    break  # Ga naar de volgende batch als deze batch succesvol is verwerkt

                except (requests.Timeout, requests.ConnectionError) as e:
                    print(f"[WARNING] Timeout/Connectiefout bij batch {batch_num}, poging {retry + 1}: {str(e)}")
                    if retry == max_retries - 1:
                        print(f"[ERROR] Batch {batch_num} mislukt na {max_retries} pogingen")
                        raise
                    time.sleep(5 * (retry + 1))  # Wacht even (exponentiële backoff) voordat opnieuw geprobeerd wordt

                except requests.RequestException as e:
                    print(f"[ERROR] Fout bij verwerken batch {batch_num}: {str(e)}")
                    print(f"[DEBUG] Response status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
                    print(
                        f"[DEBUG] Response content: {e.response.text[:200] if hasattr(e, 'response') else 'Unknown'}...")
                    raise

        return {
            "objects": response_json_list,
            "totalCount": len(response_json_list)
        }


# --- Testblok voor de APIClient ---
if __name__ == "__main__":
    # Dit blok wordt uitgevoerd als het script direct wordt gestart.
    # Hier testen we de functionaliteiten van de APIClient.

    # Haal de client credentials op uit de omgevingsvariabelen (of gebruik dummy-waarden)
    client_id = os.getenv("LUXS_PROD_CLIENT_ID", "dummy_client_id")
    client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET", "dummy_client_secret")
    base_url = os.getenv("LUXS_PROD_BASE_URL", "https://api.accept.luxsinsights.com")
    token_url = os.getenv("LUXS_PROD_TOKEN_URL", "https://api.accept.luxsinsights.com/oauth/token")

    print("[DEBUG] Initialiseren APIClient met:")
    print(f"        Client ID: {client_id}")
    print(f"        Client Secret: {client_secret}")
    print(f"        Base URL: {base_url}")

    # Maak een instantie van de APIClient
    api_client = APIClient(client_id=client_id, client_secret=client_secret, base_url=base_url, token_url=token_url)

    # Test de client door de headers op te halen
    print("[DEBUG] Test client authenticatie headers:")
    print(api_client.test_client())

    # Haal metadata op en sla deze op in een bestand
    print("[DEBUG] Ophalen volledige metadata:")
    all_metadata = api_client.get_metadata()
    with open('metadata.json', 'w') as f:
        json.dump(all_metadata, f)
    print("[DEBUG] Metadata (eerste 200 tekens):", str(all_metadata)[:200], "...")

    # Haal objecten op van een bepaald type, bijvoorbeeld 'Building'
    print("[DEBUG] Ophalen objecten van type 'Building':")
    attributes = ["Dakpartner - Building - Woonstad Rotterdam",
                  "Jaar laatste dakonderhoud - Building - Woonstad Rotterdam"]
    building_objects = api_client.get_objects(object_type="Building", attributes=attributes, only_active=True)
    print("[DEBUG] Eerste 5 objecten:")
    for obj in building_objects.get("objects", [])[:5]:
        print(obj)

    # Haal alle objecten op van het type 'Building' en toon het totaal aantal
    print("[DEBUG] Ophalen alle objecten van type 'Building':")
    all_building_objects = api_client.get_all_objects(object_type="Building", attributes=attributes, only_active=True)
    print("[DEBUG] Aantal objecten:", all_building_objects.get("totalCount", 0))
    print("[DEBUG] Eerste 5 objecten:")
    for obj in all_building_objects.get("objects", [])[:5]:
        print(obj)
