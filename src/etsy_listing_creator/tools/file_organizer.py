import os
import shutil
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging
from datetime import datetime

from pydantic import PrivateAttr, Field, validator
from crewai.tools import BaseTool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileOrganizerTool(BaseTool):
    name: str = "File Organizer Tool"
    description: str = """
    Organize files into a structured directory system for Etsy listings.
    
    This tool helps create a directory structure and copy files to appropriate locations.
    It includes validation, error handling, and backup capabilities.
    
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
      "cleanup": true,  # Optional: Whether to delete original files after copying (default: true)
      "backup": true,   # Optional: Whether to create backups before cleanup (default: true)
      "validate": true  # Optional: Whether to validate files before organizing (default: true)
    }
    
    Returns the path to the organized directory structure.
    """

    # Define the schema for the tool inputs
    listing_name: Optional[str] = Field(
        default=None, description="A descriptive name for the listing"
    )
    files: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Dictionary mapping categories to lists of file paths"
    )
    cleanup: bool = Field(
        default=True, description="Whether to delete original files after copying"
    )
    backup: bool = Field(
        default=True, description="Whether to create backups before cleanup"
    )
    should_validate: bool = Field(
        default=True, description="Whether to validate files before organizing"
    )

    # Private attributes
    _output_dir: Path = PrivateAttr()
    _backup_dir: Path = PrivateAttr()
    _allowed_extensions: Dict[str, List[str]] = PrivateAttr()

    def __init__(self, **kwargs):
        """Initialize the FileOrganizerTool."""
        # Extract output_dir before passing to super().__init__
        output_dir = kwargs.pop("output_dir", "output")

        super().__init__(**kwargs)
        self._output_dir = Path(output_dir)
        self._backup_dir = self._output_dir / "backups"
        
        # Define allowed file extensions for each category
        self._allowed_extensions = {
            "concept": [".json"],
            "original": [".png", ".jpg", ".jpeg", ".webp"],
            "prints": [".png", ".jpg", ".jpeg", ".webp"],
            "mockups": [".png", ".jpg", ".jpeg", ".webp"],
            "metadata": [".json"]
        }

        # Ensure directories exist
        os.makedirs(self._output_dir, exist_ok=True)
        os.makedirs(self._backup_dir, exist_ok=True)

        logger.info(f"FileOrganizerTool initialized with output directory: {self._output_dir}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _validate_file(self, file_path: str, category: str) -> bool:
        """Validate a file based on its category and type."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        # Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self._allowed_extensions.get(category, []):
            logger.error(f"Invalid file extension for {category}: {ext}")
            return False

        # Check file size (max 50MB)
        if os.path.getsize(file_path) > 50 * 1024 * 1024:
            logger.error(f"File too large: {file_path}")
            return False

        return True

    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create a backup of a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{os.path.basename(file_path)}_{timestamp}"
            backup_path = self._backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {str(e)}")
            return None

    def _run(
        self,
        listing_name: str,
        files: Dict[str, List[str]],
        cleanup: bool = True,
        backup: bool = True,
        should_validate: bool = True,
    ) -> str:
        """
        Organize files into a structured directory system.

        Args:
            listing_name: A descriptive name for the listing
            files: Dictionary mapping categories to lists of file paths
            cleanup: Whether to delete original files after copying
            backup: Whether to create backups before cleanup
            should_validate: Whether to validate files before organizing

        Returns:
            Path to the organized directory structure
        """
        # Generate timestamp for unique directory
        timestamp = int(time.time())

        # Sanitize listing name
        safe_name = "".join(
            c if c.isalnum() or c in [" ", "_", "-"] else "_" for c in listing_name
        )
        safe_name = safe_name.replace(" ", "_").lower()

        # Create main directory
        listing_dir = self._output_dir / f"listing_{safe_name}_{timestamp}"
        os.makedirs(listing_dir, exist_ok=True)

        logger.info(f"Created listing directory: {listing_dir}")

        # Create subdirectories
        for category in ["concept", "original", "prints", "mockups", "metadata"]:
            os.makedirs(listing_dir / category, exist_ok=True)

        # Copy files to appropriate directories
        manifest = {
            "timestamp": timestamp,
            "listing_name": listing_name,
            "files": {},
            "backups": {},
            "validation": {}
        }

        # Keep track of files to delete if cleanup is enabled
        files_to_delete = []
        missing_files = []
        validation_errors = []

        for category, file_paths in files.items():
            if category not in manifest["files"]:
                manifest["files"][category] = []

            if not file_paths:
                logger.warning(f"No files provided for category: {category}")
                continue

            for file_path in file_paths:
                if not file_path:
                    logger.warning(f"Empty file path provided for category: {category}")
                    continue
                
                # Validate file if enabled
                if should_validate and not self._validate_file(file_path, category):
                    validation_errors.append((category, file_path))
                    continue

                # Create backup if enabled
                backup_path = None
                if backup:
                    backup_path = self._create_backup(file_path)
                    if backup_path:
                        manifest["backups"][file_path] = backup_path

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
                    logger.info(f"Copied {file_path} to {dest_path}")

                    # Calculate file hash
                    file_hash = self._calculate_file_hash(dest_path)

                    # Add to manifest with metadata
                    manifest["files"][category].append({
                        "original_path": file_path,
                        "organized_path": str(dest_path),
                        "hash": file_hash,
                        "size": os.path.getsize(dest_path),
                        "timestamp": datetime.now().isoformat()
                    })

                    # Add to list of files to delete if cleanup is enabled
                    if cleanup and os.path.exists(file_path):
                        files_to_delete.append(file_path)
                except Exception as e:
                    logger.error(f"Error copying {file_path}: {str(e)}")

        # Add validation and missing files to manifest
        if validation_errors:
            manifest["validation"]["errors"] = [
                {"category": cat, "path": path} for cat, path in validation_errors
            ]
            logger.warning(f"Validation errors found: {len(validation_errors)} files")

        if missing_files:
            manifest["missing_files"] = [
                {"category": cat, "path": path} for cat, path in missing_files
            ]
            logger.warning(f"Missing files: {len(missing_files)} files")

        # Save manifest
        manifest_path = listing_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Saved manifest to {manifest_path}")

        # Clean up original files if requested
        if cleanup and files_to_delete:
            logger.info(f"Cleaning up {len(files_to_delete)} original files...")
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted original file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")

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
        for category, file_paths in files.items():
            verified_files[category] = [
                path for path in file_paths
                if os.path.exists(path)
            ]
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
        backup = input_data.get("backup", True)
        validate = input_data.get("validate", True)
        
        # Check for critical files
        critical_categories = ["concept", "metadata"]
        missing_critical = False
        
        for category in critical_categories:
            if category not in files or not files[category]:
                logger.warning(f"No files provided for critical category: {category}")
                
                # Check if the default files exist
                if category == "concept":
                    default_path = "output/concept_data.json"
                    if os.path.exists(default_path):
                        logger.info(f"Found default concept file at: {default_path}")
                        if category not in files:
                            files[category] = []
                        files[category].append(default_path)
                    else:
                        logger.error(f"Critical file not found: {default_path}")
                        missing_critical = True
                        
                elif category == "metadata":
                    default_path = "output/seo_data.json"
                    if os.path.exists(default_path):
                        logger.info(f"Found default SEO file at: {default_path}")
                        if category not in files:
                            files[category] = []
                        files[category].append(default_path)
                    else:
                        logger.error(f"Critical file not found: {default_path}")
                        missing_critical = True
        
        if missing_critical:
            logger.warning("Critical files are missing. The organization may be incomplete.")
        
        # Verify files exist before organizing
        verified_files = self._verify_files(files)
        
        # Run the tool
        return self._run(
            listing_name=listing_name,
            files=verified_files,
            cleanup=cleanup,
            backup=backup,
            should_validate=validate
        )
