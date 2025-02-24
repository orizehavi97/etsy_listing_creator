import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from src.etsy_listing_creator.tools.stability_ai import StabilityAITool

class TestStabilityAITool(unittest.TestCase):
    def setUp(self):
        # Set up environment variable for testing
        os.environ["STABILITY_KEY"] = "test_key"
        self.tool = StabilityAITool()
        
    def tearDown(self):
        # Clean up test output directory
        if Path("output/images").exists():
            for file in Path("output/images").glob("*.png"):
                file.unlink()
            Path("output/images").rmdir()
        if Path("output").exists():
            Path("output").rmdir()
        
        # Remove test environment variable safely
        os.environ.pop("STABILITY_KEY", None)

    def test_initialization(self):
        """Test if the tool initializes correctly with API key"""
        self.assertEqual(self.tool._api_key, "test_key")
        self.assertTrue(Path("output/images").exists())
        self.assertEqual(os.getenv("STABILITY_HOST"), "grpc.stability.ai:443")

    def test_initialization_without_api_key(self):
        """Test if tool raises error when API key is missing"""
        if "STABILITY_KEY" in os.environ:
            del os.environ["STABILITY_KEY"]
        
        with self.assertRaises(ValueError):
            StabilityAITool()

    @patch('stability_sdk.client.StabilityInference')
    def test_run_successful(self, mock_stability):
        """Test successful image generation"""
        # Mock the stability client response
        mock_artifact = MagicMock()
        mock_artifact.finish_reason = 1  # Normal completion
        mock_artifact.type = generation.ARTIFACT_IMAGE
        mock_artifact.seed = 123
        mock_artifact.binary = b"test_image_data"
        
        mock_response = MagicMock()
        mock_response.artifacts = [mock_artifact]
        mock_stability.return_value.generate.return_value = [mock_response]

        # Run the tool
        result = self.tool._run("test prompt")
        
        # Verify the result
        expected_path = str(Path("output/images/generated_123.png"))
        self.assertEqual(result, expected_path)
        self.assertTrue(Path(result).exists())

        # Verify the API call parameters
        mock_stability.assert_called_once_with(
            key=self.tool._api_key,
            host=os.getenv('STABILITY_HOST', 'grpc.stability.ai:443'),
            verbose=True,
        )

        mock_stability.return_value.generate.assert_called_once_with(
            prompt="test prompt",
            seed=42,
            steps=50,
            cfg_scale=8.0,
            width=1024,
            height=1024,
            samples=1,
            sampler=generation.SAMPLER_K_DPMPP_2M
        )

    @patch('stability_sdk.client.StabilityInference')
    def test_run_filter_triggered(self, mock_stability):
        """Test when safety filter is triggered"""
        # Mock the stability client response with FILTER finish reason
        mock_artifact = MagicMock()
        mock_artifact.finish_reason = generation.FILTER
        
        mock_response = MagicMock()
        mock_response.artifacts = [mock_artifact]
        mock_stability.return_value.generate.return_value = [mock_response]

        # Verify that ValueError is raised
        with self.assertRaises(ValueError) as context:
            self.tool._run("test prompt")
        
        self.assertIn("safety filters", str(context.exception))

    @patch('stability_sdk.client.StabilityInference')
    def test_run_no_image_generated(self, mock_stability):
        """Test when no image is generated"""
        # Mock empty response
        mock_stability.return_value.generate.return_value = []

        # Verify that RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            self.tool._run("test prompt")
        
        self.assertEqual(str(context.exception), "Failed to generate image")

if __name__ == '__main__':
    unittest.main() 