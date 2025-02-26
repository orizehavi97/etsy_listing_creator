"""
Test script for the JsonSaveTool.
"""

import os
import json
from pathlib import Path

from ..tools.json_save import JsonSaveTool


def test_json_save():
    """Test the JsonSaveTool with different input formats."""
    # Create a test JSON object
    test_data = {
        "title": "Test Listing",
        "description": "This is a test listing",
        "tags": ["test", "listing", "json"],
        "price": 19.99,
    }

    # Create the tool
    tool = JsonSaveTool()

    # Test with direct parameters
    result1 = tool._run(test_data, "test_direct.json")
    print(f"Test 1 result: {result1}")

    # Verify the file exists and contains the correct data
    assert os.path.exists(result1), f"File {result1} does not exist"
    with open(result1, "r") as f:
        saved_data = json.load(f)
    assert saved_data == test_data, "Saved data does not match test data"

    # Test with a dictionary containing data and filename
    input_dict = {"data": test_data, "filename": "test_dict.json"}
    result2 = tool._run(input_dict)
    print(f"Test 2 result: {result2}")

    # Verify the file exists and contains the correct data
    assert os.path.exists(result2), f"File {result2} does not exist"
    with open(result2, "r") as f:
        saved_data = json.load(f)
    assert saved_data == test_data, "Saved data does not match test data"

    # Test with a dictionary containing data and filename with output/ prefix
    input_dict = {"data": test_data, "filename": "output/test_nested.json"}
    result3 = tool._run(input_dict)
    print(f"Test 3 result: {result3}")

    # Verify the file exists and contains the correct data
    assert os.path.exists(result3), f"File {result3} does not exist"
    with open(result3, "r") as f:
        saved_data = json.load(f)
    assert saved_data == test_data, "Saved data does not match test data"

    print("All tests passed!")


if __name__ == "__main__":
    test_json_save()
