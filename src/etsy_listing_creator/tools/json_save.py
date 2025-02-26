import os
import json
from pathlib import Path
from typing import Dict, Any, Union

from pydantic import Field, PrivateAttr
from crewai.tools import BaseTool


class JsonSaveTool(BaseTool):
    name: str = "JSON Save Tool"
    description: str = """
    Save JSON data to a file in the output directory.
    
    Input should be either:
    1. Two separate parameters:
       - data: A JSON string or dictionary containing the data to save
       - filename: Name of the file to save (e.g., "listing.json")
       
    2. Or a single dictionary with:
       - data: The data to save
       - filename: The filename to use
       
    Do NOT include "output/" in the filename - the tool automatically saves to the output directory.
    
    Returns the path to the saved file.
    """

    # Private attributes using Pydantic's PrivateAttr
    _output_dir: Path = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._output_dir = Path("output")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(
        self, data: Union[str, Dict[str, Any]], filename: str = "listing.json"
    ) -> str:
        """
        Save JSON data to a file.

        Args:
            data: JSON data as a string or dictionary
            filename: Name of the file to save (default: listing.json)

        Returns:
            Path to the saved file
        """
        # Ensure the output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Handle the case where data is passed as a dictionary with 'data' and 'filename' keys
        if isinstance(data, dict) and "data" in data and "filename" in data:
            json_data = data["data"]
            filename = data["filename"]
            # If filename already includes 'output/', remove it to prevent nesting
            if filename.startswith("output/"):
                filename = filename.replace("output/", "", 1)
        else:
            # Prepare the data normally
            if isinstance(data, str):
                try:
                    # Try to parse the string as JSON
                    json_data = json.loads(data)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON string provided")
            elif isinstance(data, dict):
                json_data = data
            else:
                raise TypeError("Data must be a JSON string or dictionary")

        # Create the file path, ensuring we don't nest output directories
        file_path = self._output_dir / filename

        # Save the data
        try:
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            print(f"✓ JSON data saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"Error saving JSON data: {str(e)}")
            raise RuntimeError(f"Failed to save JSON data: {str(e)}")
