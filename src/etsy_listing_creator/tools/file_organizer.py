import os
import shutil
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from pydantic import PrivateAttr, Field
from crewai.tools import BaseTool


class FileOrganizerTool(BaseTool):
    name: str = "File Organizer Tool"
    description: str = """
    Organize files into a structured directory system for Etsy listings.
    
    This tool helps create a directory structure and copy files to appropriate locations.
    
    Input should be a JSON object with the following structure:
    {
      "listing_name": "descriptive_name",  # Used as part of the directory name
      "files": {
        "concept": ["path/to/concept/file.json"],
        "original": ["path/to/original/image.png"],
        "prints": ["path/to/print1.png", "path/to/print2.png"],
        "mockups": ["path/to/mockup1.png", "path/to/mockup2.png"],
        "metadata": ["path/to/metadata.json"]
      },
      "cleanup": true  # Optional: Whether to delete original files after copying (default: true)
    }
    
    Returns the path to the organized directory structure.
    """

    # Define the schema for the tool inputs - make them Optional for initialization
    listing_name: Optional[str] = Field(
        default=None, description="A descriptive name for the listing"
    )
    files: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Dictionary mapping categories to lists of file paths"
    )
    cleanup: bool = Field(
        default=True, description="Whether to delete original files after copying"
    )

    # Private attributes using Pydantic's PrivateAttr
    _output_dir: Path = PrivateAttr()

    def __init__(self, **kwargs):
        """Initialize the FileOrganizerTool."""
        # Extract output_dir before passing to super().__init__
        output_dir = kwargs.pop("output_dir", "output")

        super().__init__(**kwargs)
        self._output_dir = Path(output_dir)

        # Ensure the output directory exists
        os.makedirs(self._output_dir, exist_ok=True)

        print(
            f"FileOrganizerTool initialized with output directory: {self._output_dir}"
        )

    def _run(
        self,
        listing_name: str,
        files: Dict[str, List[str]],
        cleanup: bool = True,
    ) -> str:
        """
        Organize files into a structured directory system.

        Args:
            listing_name: A descriptive name for the listing (used in directory name)
            files: Dictionary mapping categories to lists of file paths
            cleanup: Whether to delete the original files after copying (defaults to True)

        Returns:
            Path to the organized directory structure
        """
        # Generate timestamp for unique directory
        timestamp = int(time.time())

        # Sanitize listing name for use in directory name
        safe_name = "".join(
            c if c.isalnum() or c in [" ", "_", "-"] else "_" for c in listing_name
        )
        safe_name = safe_name.replace(" ", "_").lower()

        # Create main directory
        listing_dir = self._output_dir / f"listing_{safe_name}_{timestamp}"
        os.makedirs(listing_dir, exist_ok=True)

        print(f"Created listing directory: {listing_dir}")

        # Create subdirectories
        for category in ["concept", "original", "prints", "mockups", "metadata"]:
            os.makedirs(listing_dir / category, exist_ok=True)

        # Copy files to appropriate directories
        manifest = {"timestamp": timestamp, "listing_name": listing_name, "files": {}}

        # Keep track of files to delete if cleanup is enabled
        files_to_delete = []
        missing_files = []

        for category, file_paths in files.items():
            if category not in manifest["files"]:
                manifest["files"][category] = []

            if not file_paths:
                print(f"Warning: No files provided for category: {category}")
                continue

            for file_path in file_paths:
                if not file_path:
                    print(f"Warning: Empty file path provided for category: {category}")
                    continue
                
                if not os.path.exists(file_path):
                    print(f"Warning: File not found: {file_path} (category: {category})")
                    missing_files.append((category, file_path))
                    continue

                # Get the filename from the path
                filename = os.path.basename(file_path)

                # Create a descriptive name
                base, ext = os.path.splitext(filename)
                new_filename = f"{category}_{base}{ext}"

                # Destination path
                dest_path = listing_dir / category / new_filename

                try:
                    # Copy the file
                    shutil.copy2(file_path, dest_path)
                    print(f"Copied {file_path} to {dest_path}")

                    # Add to manifest
                    manifest["files"][category].append(str(dest_path))

                    # Add to list of files to delete if cleanup is enabled
                    if cleanup and os.path.exists(file_path):
                        files_to_delete.append(file_path)
                except Exception as e:
                    print(f"Error copying {file_path}: {str(e)}")

        # If there were missing files, add them to the manifest
        if missing_files:
            manifest["missing_files"] = [{"category": cat, "path": path} for cat, path in missing_files]
            print(f"Warning: {len(missing_files)} files were not found and could not be copied.")

        # Save manifest
        manifest_path = listing_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"Saved manifest to {manifest_path}")

        # Clean up original files if requested
        if cleanup and files_to_delete:
            print(f"Cleaning up {len(files_to_delete)} original files...")
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"Deleted original file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {str(e)}")

        # Return the path to the organized directory
        return str(listing_dir)

    def _verify_files(self, files: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Verify that all files exist and return a filtered dictionary with only existing files.
        
        Args:
            files: Dictionary mapping categories to lists of file paths
            
        Returns:
            Dictionary with only existing files
        """
        verified_files = {}
        missing_files = []
        
        for category, file_paths in files.items():
            verified_files[category] = []
            
            if not file_paths:
                print(f"Warning: No files provided for category: {category}")
                continue
                
            for file_path in file_paths:
                if not file_path:
                    print(f"Warning: Empty file path provided for category: {category}")
                    continue
                    
                if os.path.exists(file_path):
                    verified_files[category].append(file_path)
                    print(f"Verified file exists: {file_path} (category: {category})")
                else:
                    missing_files.append((category, file_path))
                    print(f"Warning: File not found: {file_path} (category: {category})")
        
        if missing_files:
            print(f"Warning: {len(missing_files)} files were not found and will be skipped.")
            
        return verified_files

    def run(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """
        Run the FileOrganizerTool with the provided input.

        Args:
            input_data: Either a JSON string or a dictionary with listing_name and files

        Returns:
            Path to the organized directory structure
        """
        # Parse input if it's a string
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                raise ValueError("Input must be a valid JSON string or dictionary")

        # Validate input
        if not isinstance(input_data, dict):
            raise ValueError(
                "Input must be a dictionary or JSON string representing a dictionary"
            )

        if "listing_name" not in input_data:
            raise ValueError("Input must contain a 'listing_name' field")

        if "files" not in input_data:
            raise ValueError("Input must contain a 'files' field")

        # Extract parameters
        listing_name = input_data["listing_name"]
        files = input_data["files"]
        cleanup = input_data.get("cleanup", True)
        
        # Check for critical files
        critical_categories = ["concept", "metadata"]
        missing_critical = False
        
        for category in critical_categories:
            if category not in files or not files[category]:
                print(f"Warning: No files provided for critical category: {category}")
                
                # Check if the default files exist
                if category == "concept":
                    default_path = "output/concept_data.json"
                    if os.path.exists(default_path):
                        print(f"Found default concept file at: {default_path}")
                        if category not in files:
                            files[category] = []
                        files[category].append(default_path)
                    else:
                        print(f"Critical file not found: {default_path}")
                        missing_critical = True
                        
                elif category == "metadata":
                    default_path = "output/seo_data.json"
                    if os.path.exists(default_path):
                        print(f"Found default SEO file at: {default_path}")
                        if category not in files:
                            files[category] = []
                        files[category].append(default_path)
                    else:
                        print(f"Critical file not found: {default_path}")
                        missing_critical = True
        
        if missing_critical:
            print("Warning: Critical files are missing. The organization may be incomplete.")
        
        # Verify files exist before organizing
        verified_files = self._verify_files(files)
        
        # Run the tool
        return self._run(listing_name=listing_name, files=verified_files, cleanup=cleanup)
