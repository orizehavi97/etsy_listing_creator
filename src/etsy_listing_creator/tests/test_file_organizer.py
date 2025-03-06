import os
import json
import shutil
import tempfile
from pathlib import Path

# Use relative import
from ..tools import FileOrganizerTool


def test_file_organizer():
    """Test the FileOrganizerTool functionality."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    try:
        # Create output directory inside temp_dir
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Create test files
        test_files = {
            "concept": [],
            "original": [],
            "prints": [],
            "mockups": [],
            "metadata": [],
        }

        # Create a test concept file
        concept_path = os.path.join(temp_dir, "concept.json")
        with open(concept_path, "w") as f:
            json.dump(
                {"style": "minimalist", "theme": "nature", "aspect_ratio": "landscape"},
                f,
            )
        test_files["concept"].append(concept_path)

        # Create a test original image file
        original_path = os.path.join(temp_dir, "original.png")
        with open(original_path, "w") as f:
            f.write("This is a mock image file")
        test_files["original"].append(original_path)

        # Create test print files
        for i in range(3):
            print_path = os.path.join(temp_dir, f"print_{i}.png")
            with open(print_path, "w") as f:
                f.write(f"This is print {i}")
            test_files["prints"].append(print_path)

        # Create test mockup files
        for i in range(2):
            mockup_path = os.path.join(temp_dir, f"mockup_{i}.png")
            with open(mockup_path, "w") as f:
                f.write(f"This is mockup {i}")
            test_files["mockups"].append(mockup_path)

        # Create a test metadata file
        metadata_path = os.path.join(temp_dir, "seo.json")
        with open(metadata_path, "w") as f:
            json.dump({"title": "Test Title", "tags": ["test", "example"]}, f)
        test_files["metadata"].append(metadata_path)

        # Initialize the FileOrganizerTool with our test output directory
        organizer = FileOrganizerTool(output_dir=output_dir)

        # Run the tool
        result = organizer.run({"listing_name": "Test Listing", "files": test_files})

        print(f"Organized directory: {result}")

        # Verify the result is a string (path)
        assert isinstance(result, str), "Result should be a string path"

        # Verify the directory exists
        assert os.path.exists(result), "Organized directory should exist"

        # Verify subdirectories exist
        for subdir in ["concept", "original", "prints", "mockups", "metadata"]:
            subdir_path = os.path.join(result, subdir)
            assert os.path.exists(subdir_path), f"Subdirectory {subdir} should exist"

            # Verify files were copied to each subdirectory
            if subdir in test_files and test_files[subdir]:
                assert (
                    len(os.listdir(subdir_path)) > 0
                ), f"Subdirectory {subdir} should contain files"

        # Verify manifest.json exists
        manifest_path = os.path.join(result, "manifest.json")
        assert os.path.exists(manifest_path), "manifest.json should exist"

        # Verify manifest.json content
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            assert "timestamp" in manifest, "Manifest should contain timestamp"
            assert "listing_name" in manifest, "Manifest should contain listing_name"
            assert "files" in manifest, "Manifest should contain files"

            # Verify all categories are in the manifest
            for category in test_files.keys():
                assert (
                    category in manifest["files"]
                ), f"Manifest should contain {category} category"

        print("All tests passed!")

    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_file_organizer()
