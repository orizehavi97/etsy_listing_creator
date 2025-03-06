import os
import json
from pathlib import Path
from typing import Dict, Any, Union, Optional

from pydantic import Field, PrivateAttr, BaseModel
from crewai.tools import BaseTool


class JsonSaveToolSchema(BaseModel):
    data: Union[str, Dict[str, Any]] = Field(description="JSON data as a string or dictionary")
    filename: str = Field(default="listing.json", description="Name of the file to save")


class JsonSaveTool(BaseTool):
    name: str = "JSON Save Tool"
    description: str = """
    Save JSON data to a file in the output directory or any subdirectory.
    
    Input should be either:
    1. Two separate parameters:
       - data: A JSON string or dictionary containing the data to save
       - filename: Name of the file to save (e.g., "listing.json" or "listing_dir/metadata/listing.json")
       
    2. Or a single dictionary with:
       - data: The data to save
       - filename: The filename to use
       
    You can include subdirectories in the filename (e.g., "listing_dir/metadata/listing.json").
    The tool will automatically create any necessary directories.
    
    Returns the path to the saved file.
    """
    
    schema = JsonSaveToolSchema

    # Private attributes using Pydantic's PrivateAttr
    _output_dir: Path = PrivateAttr()
    _project_root: Path = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set the project root to the directory where the script is run from
        self._project_root = Path(os.getcwd())
        print(f"Project root directory: {self._project_root}")
        
        # Set the output directory to be relative to the project root
        self._output_dir = self._project_root / "output"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {self._output_dir}")

    def _run(
        self, data: Union[str, Dict[str, Any]], filename: str = "listing.json"
    ) -> str:
        """
        Save JSON data to a file.

        Args:
            data: JSON data as a string or dictionary
            filename: Name of the file to save, can include subdirectories (e.g., "listing_dir/metadata/listing.json")

        Returns:
            Path to the saved file
        """
        # Ensure the output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Handle the case where data is passed as a dictionary with 'data' and 'filename' keys
        if isinstance(data, dict) and "data" in data and "filename" in data:
            json_data = data["data"]
            filename = data["filename"]
        else:
            # Prepare the data normally
            if isinstance(data, str):
                try:
                    # Try to parse the string as JSON
                    json_data = json.loads(data)
                except json.JSONDecodeError:
                    error_msg = "Invalid JSON string provided"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
            elif isinstance(data, dict):
                json_data = data
            else:
                error_msg = "Data must be a JSON string or dictionary"
                print(f"Error: {error_msg}")
                raise TypeError(error_msg)

        # Normalize the filename to ensure consistent path handling
        # If filename starts with 'output/', remove it to prevent nesting
        if filename.startswith("output/"):
            filename = filename.replace("output/", "", 1)
            print(f"Normalized filename to prevent nesting: {filename}")
        
        # Create the file path, ensuring we don't nest output directories
        file_path = self._output_dir / filename
        print(f"Full file path: {file_path}")

        # Save the data
        try:
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Created parent directories: {file_path.parent}")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            print(f"✓ JSON data saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            error_msg = f"Failed to save JSON data: {str(e)}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg)

    def run(self, tool_input: Union[str, Dict[str, Any]]) -> str:
        """
        Run the tool with the given input.

        Args:
            tool_input: Input to the tool, can be a JSON string, a dictionary, or a dictionary with 'data' and 'filename' keys

        Returns:
            Path to the saved file
        """
        try:
            # Handle different input formats
            if isinstance(tool_input, str):
                try:
                    # Try to parse as JSON
                    input_data = json.loads(tool_input)
                    
                    # Check if it's a dictionary with 'data' and 'filename' keys
                    if isinstance(input_data, dict) and "data" in input_data:
                        return self._run(
                            data=input_data["data"],
                            filename=input_data.get("filename", "listing.json")
                        )
                    else:
                        # It's a JSON object to be saved directly
                        print("Input is a JSON string to be saved directly")
                        return self._run(
                            data=input_data,
                            filename="output/data.json"
                        )
                except json.JSONDecodeError:
                    # Not valid JSON, treat as a filename and save empty data
                    print(f"Warning: Input is not valid JSON: {tool_input}")
                    return self._run(
                        data={},
                        filename=tool_input
                    )
            elif isinstance(tool_input, dict):
                # Check if it's a dictionary with 'data' and 'filename' keys
                if "data" in tool_input:
                    return self._run(
                        data=tool_input["data"],
                        filename=tool_input.get("filename", "listing.json")
                    )
                else:
                    # It's a JSON object to be saved directly
                    print("Input is a dictionary to be saved directly")
                    
                    # Check if there's a _filename hint in the dictionary
                    filename = "output/data.json"
                    if "_filename" in tool_input:
                        filename = tool_input.pop("_filename")  # Remove the hint before saving
                        print(f"Found _filename hint: {filename}")
                    
                    return self._run(
                        data=tool_input,
                        filename=filename
                    )
            else:
                raise ValueError(f"Unsupported input type: {type(tool_input)}")
        except Exception as e:
            error_msg = f"Error in JsonSaveTool.run: {str(e)}"
            print(f"Error: {error_msg}")
            return f"Error: {error_msg}"
