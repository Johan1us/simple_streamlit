import logging

logging.basicConfig(level=logging.DEBUG)


# class DatasetManager:
#     def __init__(self, config_folder: Union[str, Path]) -> None:
#         # Allow config_folder to be passed as either a string or a Path.
#         self.config_folder = Path(config_folder) if isinstance(config_folder, str) else config_folder
#         self.api_client = self._initialize_api_client()
#
#     def _initialize_api_client(self) -> APIClient:
#         # You can switch between test and production credentials by commenting/uncommenting below.
#         # client_id = os.getenv("LUXS_ACCEPT_CLIENT_ID")
#         # client_secret = os.getenv("LUXS_ACCEPT_CLIENT_SECRET")
#         # base_url = "https://api.accept.luxsinsights.com"
#
#         client_id = os.getenv("LUXS_PROD_CLIENT_ID")
#         client_secret = os.getenv("LUXS_PROD_CLIENT_SECRET")
#         base_url = "https://api.prod.luxsinsights.com"
#
#         return APIClient(client_id=client_id, client_secret=client_secret, base_url=base_url)
#
#     def _load_configs(self) -> List[Dict[str, Any]]:
#         """Load all JSON config files from the configuration folder."""
#         configs = []
#         for config_file in self.config_folder.glob("*.json"):
#             try:
#                 data = json.loads(config_file.read_text(encoding="utf-8"))
#                 # Save the filename (without extension) for later use.
#                 data["__filename__"] = config_file.stem
#                 configs.append(data)
#             except Exception as e:
#                 logging.error(f"Error reading config file {config_file}: {e}")
#         return configs
#
#     def get_available_datasets(self) -> List[str]:
#         configs = self._load_configs()
#         # Prepend a selection prompt to the list.
#         datasets = [cfg.get("dataset") for cfg in configs if "dataset" in cfg]
#         return ["Selecteer dataset"] + datasets
#
#     def get_dataset_config(self, dataset_name: str) -> Optional[Dict[str, Any]]:
#         for cfg in self._load_configs():
#             if cfg.get("dataset") == dataset_name:
#                 return cfg
#         return None
#
#     def get_object_type(self, dataset_name: str) -> Optional[str]:
#         for cfg in self._load_configs():
#             if cfg.get("dataset") == dataset_name:
#                 return cfg.get("objectType")
#         return None
#
#     def get_file_name(self, dataset_name: str) -> Optional[str]:
#         for cfg in self._load_configs():
#             if cfg.get("dataset") == dataset_name:
#                 # Return the filename stored in the config (without .json)
#                 return cfg.get("__filename__")
#         return None




# def handle_excel_download(config: Dict[str, Any], api_client: APIClient) -> bytes:
#     """Download the dataset from the API and create an Excel file."""
#     object_type = config["objectType"]
#     attribute_names = [attr["AttributeName"] for attr in config.get("attributes", [])]
#
#     # Retrieve metadata and data from the API.
#     metadata = api_client.get_metadata(object_type)
#     st.success("Metadata opgehaald van de API")
#     response_data = api_client.get_all_objects(
#         object_type=object_type,
#         attributes=attribute_names,
#         only_active=True,
#         st=st,
#     )
#     st.success("Dataset opgehaald van de API")
#
#     dataset_data = response_data.get("objects", [])
#     logging.debug(f"Number of objects: {len(dataset_data)}")
#     if dataset_data:
#         logging.debug(f"First object sample: {dataset_data[0]}")
#
#     columns_mapping = {attr["excelColumnName"]: attr["AttributeName"] for attr in config.get("attributes", [])}
#     metadata_map = build_metadata_map(metadata, config)
#
#     handler = ExcelHandler(metadata=metadata_map, columns_mapping=columns_mapping, object_type=object_type)
#     excel_file = handler.create_excel_file(data=dataset_data)
#
#     st.write("Preview van de eerste 5 rijen van de Excel file:")
#     preview_df = pd.read_excel(excel_file)
#     st.dataframe(preview_df.head(5), hide_index=True)
#
#     return excel_file


# def build_metadata_map(metadata: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
#     """Build a mapping of metadata for each attribute in the configuration."""
#     object_type = config["objectType"]
#     ot_data = next(
#         (ot for ot in metadata.get("objectTypes", []) if ot.get("name") == object_type), None
#     )
#     if not ot_data:
#         raise ValueError(f"Object type {object_type} not found in metadata")
#
#     # Create a more flexible mapping that matches on partial names
#     metadata_by_name = {}
#     for attr in ot_data.get("attributes", []):
#         # Store both the full name and a simplified version (without the suffix)
#         full_name = attr["name"]
#         simple_name = full_name.split(" - ")[0] if " - " in full_name else full_name
#         metadata_by_name[full_name] = attr
#         metadata_by_name[simple_name] = attr
#
#     meta_map = {}
#     for attr_def in config.get("attributes", []):
#         attr_name = attr_def["AttributeName"]
#         meta = metadata_by_name.get(attr_name, {})
#         meta_map[attr_name] = meta
#     return meta_map


# def convert_cell_value(
#     col: str,
#     api_field: str,
#     value: Any,
#     metadata: Dict[str, Any]
# ) -> Optional[Union[int, str]]:
#     """
#     Convert a value read from the Excel cell to the expected format for the API based on metadata.
#
#     Args:
#         col: Excel column name
#         api_field: API field name
#         value: Value to convert
#         metadata: Metadata for this field from the API
#     """
#     # Skip conversion for null values
#     if pd.isnull(value):
#         return None
#
#     field_type = metadata.get("type", "").upper()
#     date_format = metadata.get("dateFormat")
#
#     # Handle different data types based on metadata
#     if field_type == "INT":
#         try:
#             return int(float(value))
#         except (ValueError, TypeError):
#             st.write(f"Error converting {value} to integer for field {col}")
#             return None
#
#     elif field_type == "DATE":
#         try:
#             if isinstance(value, pd.Timestamp):
#                 if date_format == "yyyy":
#                     return str(value.year)
#                 elif date_format == "dd-MM-yyyy":
#                     return value.strftime("%d-%m-%Y")
#                 elif date_format == "yyyy-MM-dd":
#                     return value.strftime("%Y-%m-%d")
#                 else:
#                     return value.strftime("%Y-%m-%d")  # default format
#             else:
#                 # Handle string/number inputs
#                 if date_format == "yyyy":
#                     return str(int(float(value)))
#                 else:
#                     year = int(float(value))
#                     if date_format == "dd-MM-yyyy":
#                         return f"31-12-{year}"
#                     elif date_format == "yyyy-MM-dd":
#                         return f"{year}-12-31"
#                     else:
#                         return str(year)
#         except Exception as e:
#             st.write(f"Error converting date value {value} for field {col}: {e}")
#             return None
#
#     elif field_type == "FLOAT":
#         try:
#             float_val = float(value)
#             # Return as integer if it's a whole number
#             return int(float_val) if float_val.is_integer() else str(float_val)
#         except (ValueError, TypeError):
#             return str(value)
#
#     # Default to string conversion for other types
#     return str(value)


# class DataTypeMapper:
#     """
#     Class responsible for converting values between Excel and API formats based on metadata.
#     """
#     def __init__(self, metadata_map: Dict[str, Any]):
#         self.metadata_map = metadata_map
#
#     def convert_value(self, col: str, api_field: str, value: Any, field_metadata: Dict[str, Any]) -> Optional[Union[int, str]]:
#         """
#         Convert a value based on its metadata type and format.
#
#         Args:
#             col: Excel column name
#             api_field: API field name
#             value: Value to convert
#             field_metadata: Metadata for this field from the API
#         """
#         if pd.isnull(value):
#             return None
#
#         field_type = field_metadata.get("type", "").upper()
#
#         # Dispatch to appropriate conversion method based on type
#         if field_type == "DATE":
#             return self._convert_date(value, field_metadata.get("dateFormat"))
#         elif field_type == "INT":
#             return self._convert_int(value)
#         elif field_type == "FLOAT":
#             return self._convert_float(value)
#         else:
#             return self._convert_string(value)
#
#     def _convert_date(self, value: Any, date_format: Optional[str]) -> Optional[str]:
#         """Convert a value to the specified date format."""
#         try:
#             # Convert to datetime if not already
#             if not isinstance(value, pd.Timestamp):
#                 value = pd.to_datetime(value)
#
#             # Format according to specified format
#             if date_format == "yyyy":
#                 return str(value.year)
#             elif date_format == "dd-MM-yyyy":
#                 return value.strftime("%d-%m-%Y")
#             elif date_format == "yyyy-MM-dd":
#                 return value.strftime("%Y-%m-%d")
#             else:
#                 return value.strftime("%Y-%m-%d")  # default format
#
#         except Exception as e:
#             st.write(f"Error converting date value {value}: {e}")
#             return None
#
#     def _convert_int(self, value: Any) -> Optional[int]:
#         """Convert a value to integer."""
#         try:
#             return int(float(value))
#         except (ValueError, TypeError):
#             st.write(f"Error converting {value} to integer")
#             return None
#
#     def _convert_float(self, value: Any) -> Union[int, str]:
#         """Convert a value to float/integer."""
#         try:
#             float_val = float(value)
#             # Return as integer if it's a whole number
#             return int(float_val) if float_val.is_integer() else str(float_val)
#         except (ValueError, TypeError):
#             return str(value)
#
#     def _convert_string(self, value: Any) -> str:
#         """Convert a value to string."""
#         return str(value)






