import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from etsy_listing_creator.tools.replicate import ReplicateImageTool


class TestReplicateImageTool(unittest.TestCase):
    @patch("replicate.run")
    @patch("requests.get")
    def test_run_with_mock(self, mock_get, mock_run):
        # Set up mocks
        mock_run.return_value = ["https://example.com/image.webp"]

        # Mock the response for downloading the image
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake image data"]
        mock_get.return_value = mock_response

        # Create the tool
        tool = ReplicateImageTool()

        # Run the tool
        result = tool._run("A beautiful sunset over the ocean")

        # Check that the tool called replicate.run with the correct parameters
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], tool._model_id)
        self.assertIn("prompt", kwargs["input"])
        self.assertEqual(kwargs["input"]["prompt"], "A beautiful sunset over the ocean")

        # Check that the tool downloaded the image
        mock_get.assert_called_once_with("https://example.com/image.webp", stream=True)

        # Check that the result is a path to a file
        self.assertTrue(isinstance(result, str))
        self.assertTrue(result.endswith(".webp"))

        # Clean up the test file if it exists
        if os.path.exists(result):
            os.remove(result)


if __name__ == "__main__":
    unittest.main()
