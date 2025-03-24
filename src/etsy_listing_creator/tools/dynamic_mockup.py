import os
from pathlib import Path
from typing import List, Dict, Optional
import json

import requests
from pydantic import Field, PrivateAttr, BaseModel

from crewai.tools import BaseTool


class DynamicMockupToolSchema(BaseModel):
    image_path: str = Field(description="Path to the input image file")
    template_names: Optional[List[str]] = Field(default=None, description="Optional list of template names to use")
    aspect_ratio: Optional[str] = Field(default=None, description="The aspect ratio to use ('portrait', 'landscape', or None for default)")


class DynamicMockupTool(BaseTool):
    name: str = "Dynamic Mockups Generator"
    description: str = """
    Create professional product mockups using Dynamic Mockups API.
    Input should be a path to an image file.
    Returns a list of paths to the generated mockup files.
    """
    
    schema = DynamicMockupToolSchema

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://app.dynamicmockups.com/api/v1")

    # Portrait-oriented templates (3:4 aspect ratio)
    _portrait_templates: Dict[str, Dict[str, str]] = PrivateAttr(
        default={
            "1_p": {
                "mockup_uuid": "fa9a9b28-2ed4-4e38-8b34-6968192b513b",
                "smart_object_uuid": "b60eb5f7-e1c3-48aa-88ee-1a2b8e713c2b",
            },
            "2_p": {
                "mockup_uuid": "0575ee59-47c2-4cb5-bb85-f6ef4295494d",
                "smart_object_uuid": "90ba62ab-460e-4762-8c07-ff81f391f8e7",
            },
            "3_p": {
                "mockup_uuid": "801e24ac-981f-4ba8-a70b-e39d0ba9bebf",
                "smart_object_uuid": "ebbbdf68-b351-4f0f-8f1f-f65427d5dbff",
            },
            "4_p": {
                "mockup_uuid": "1fc4c170-87aa-451c-9a10-5988d48b2b6d",
                "smart_object_uuid": "cb7e2c6b-400f-4fd9-9b51-eae4681f5de3",
            },

        }
    )

    # Landscape-oriented templates (4:3 aspect ratio)
    _landscape_templates: Dict[str, Dict[str, str]] = PrivateAttr(
        default={
            "1_l": {
                "mockup_uuid": "67ab2a9d-adee-4ff0-9e64-c897628a1d77",
                "smart_object_uuid": "79608905-51fc-4b63-889d-c93dd6aa5784",
            },
            "2_l": {
                "mockup_uuid": "64e30038-8554-4290-acdf-530c5f77c146",
                "smart_object_uuid": "377b3c81-618d-437b-a179-44afb1d83347",
            },
            "3_l": {
                "mockup_uuid": "ce75acf7-ff28-4976-9ac1-354359d4b87e",
                "smart_object_uuid": "410cdf57-4f0e-4b4d-b4a6-2cf09b28e87e",
            },
            "4_l": {
                "mockup_uuid": "051c159e-9a1e-4b22-a1be-79cc4e074a85",
                "smart_object_uuid": "9342e55c-71ce-4e06-bb98-3e90615522f2",
            },
        }
    )

    # Default templates (for backward compatibility)
    _templates: Dict[str, Dict[str, str]] = PrivateAttr(
        default={
            "frame-mockup": {
                "mockup_uuid": "88ad0ec7-4b34-4be4-a762-154d64229d07",
                "smart_object_uuid": "89f5a078-8770-4cb8-9e53-acdd45663c76",
            },
            "wall-art-mockup": {
                "mockup_uuid": "efcfbd73-338c-46f2-a69c-439acd75d5c2",
                "smart_object_uuid": "4f3ca126-a427-4360-89e2-4505d60479a7",
            },
            "canvas-print-mockup": {
                "mockup_uuid": "54f260fc-215a-480e-81e0-5328936a5650",
                "smart_object_uuid": "1efadc65-88ce-4d72-83e1-375a11400960",
            },
            "poster-mockup": {
                "mockup_uuid": "5d47f14a-629b-49e8-9f8b-c27e5332f404",
                "smart_object_uuid": "cd7919b0-a9c0-4ee0-851f-004102c60af8",
            },
            "living-room-mockup": {
                "mockup_uuid": "07bfe149-564c-4f50-bf7f-ae73f8bc870c",
                "smart_object_uuid": "7f853dca-02f9-4e42-9eed-7bb227bc999e",
            },
        }
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("DYNAMIC_MOCKUPS_API_KEY")
        if not self._api_key:
            raise ValueError("DYNAMIC_MOCKUPS_API_KEY environment variable is required")

        self._output_dir = Path("output/mockups")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def get_templates_for_aspect_ratio(
        self, aspect_ratio: str = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Get the appropriate templates for the specified aspect ratio.

        Args:
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            Dictionary of templates appropriate for the aspect ratio
        """
        if aspect_ratio == "portrait":
            print("Using portrait-oriented templates (3:4 aspect ratio)")
            return self._portrait_templates
        elif aspect_ratio == "landscape":
            print("Using landscape-oriented templates (4:3 aspect ratio)")
            return self._landscape_templates
        else:
            print("Using default templates (no specific aspect ratio)")
            return self._templates

    def select_templates(
        self, template_names: List[str] = None, aspect_ratio: str = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Select specific mockup templates to use.

        Args:
            template_names: List of template names to use. If None, all templates will be used.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            Dictionary of selected templates
        """
        # Get the appropriate templates for the aspect ratio
        templates = self.get_templates_for_aspect_ratio(aspect_ratio)

        if template_names is None:
            # Use all templates for the specified aspect ratio
            return templates

        selected_templates = {}
        for name in template_names:
            # Convert descriptive names to numbered templates
            if aspect_ratio == "landscape":
                if name == "landscape-frame-mockup":
                    selected_templates["1_l"] = templates["1_l"]
                elif name == "landscape-wall-art-mockup":
                    selected_templates["2_l"] = templates["2_l"]
                elif name == "landscape-canvas-print-mockup":
                    selected_templates["3_l"] = templates["3_l"]
                elif name == "landscape-poster-mockup":
                    selected_templates["4_l"] = templates["4_l"]
            elif aspect_ratio == "portrait":
                if name == "portrait-frame-mockup":
                    selected_templates["1_p"] = templates["1_p"]
                elif name == "portrait-wall-art-mockup":
                    selected_templates["2_p"] = templates["2_p"]
                elif name == "portrait-canvas-print-mockup":
                    selected_templates["3_p"] = templates["3_p"]
                elif name == "portrait-poster-mockup":
                    selected_templates["4_p"] = templates["4_p"]
            elif name in templates:
                selected_templates[name] = templates[name]
            else:
                print(
                    f"Warning: Template '{name}' not found for aspect ratio '{aspect_ratio}'. "
                    f"Available templates: {list(templates.keys())}"
                )

        if not selected_templates:
            # If no valid templates were selected, use all templates for the specified aspect ratio
            print(
                f"No valid templates selected for aspect ratio '{aspect_ratio}'. Using all available templates."
            )
            return templates

        return selected_templates

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self._api_key,
        }

    def _handle_error_response(
        self, response: requests.Response, template_name: str = None
    ) -> None:
        """Handle error responses from the API"""
        try:
            error_data = response.json()
            error_message = error_data.get("message", "")
            error_details = error_data.get("errors", {})
            print(f"Error response: {error_data}")  # Add more detailed error logging
        except:
            error_message = response.text
            error_details = {}
            print(f"Raw error response: {response.text}")  # Add raw error logging

        if response.status_code == 401:
            raise ValueError("Unauthorized - Invalid API key")
        elif response.status_code == 422:
            if "mockup_uuid" in error_details:
                raise ValueError(f"Invalid mockup UUID: {error_message}")
            else:
                raise ValueError(f"Validation error: {error_message}")
        elif response.status_code == 429:
            raise RuntimeError("Rate limit exceeded (300 calls per minute)")
        elif response.status_code == 400:
            if template_name:  # Partial failure
                return None
            else:  # Complete failure
                raise RuntimeError(f"Bad request: {error_message}")
        elif response.status_code >= 500:
            raise RuntimeError("Server error occurred. Please try again later.")
        else:  # Other errors
            raise RuntimeError(
                f"API request failed ({response.status_code}): {error_message}"
            )

    def _upload_image(self, image_path: str) -> str:
        """
        Upload an image to ImgBB and get a public URL.

        Args:
            image_path: Path to the image file to upload

        Returns:
            Public URL of the uploaded image
        """
        upload_url = "https://api.imgbb.com/1/upload"

        # Verify the image exists
        if not os.path.exists(image_path):
            raise ValueError(f"Image file not found: {image_path}")

        imgbb_key = os.getenv("IMGBB_API_KEY")
        if not imgbb_key:
            raise ValueError(
                "IMGBB_API_KEY environment variable is required for image uploading"
            )

        try:
            # Prepare the file for upload
            with open(image_path, "rb") as img_file:
                # ImgBB expects the image as base64
                import base64

                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Make the request
            print(f"Uploading image: {image_path}")
            response = requests.post(
                upload_url,
                data={
                    "key": imgbb_key,
                    "image": image_data,
                },
                timeout=30,
            )

            # Check response
            if response.status_code != 200:
                print(f"Upload failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                raise RuntimeError(f"Failed to upload image: {response.text}")

            # Parse response
            result = response.json()
            if not result.get("success"):
                print(f"Upload failed: {result}")
                raise RuntimeError("Upload failed")

            # Get the URL - ImgBB provides several URLs, we'll use the direct display URL
            url = result["data"]["display_url"]
            print(f"✓ Image uploaded successfully to: {url}")
            return url

        except Exception as e:
            print(f"Error uploading image: {str(e)}")
            raise RuntimeError(f"Failed to upload image: {str(e)}")

    def _run(
        self,
        image_path: str,
        template_names: List[str] = None,
        aspect_ratio: str = None,
    ) -> List[str]:
        """
        Generate product mockups using Dynamic Mockups API.

        Args:
            image_path: Path to the input image file or URL to an image
            template_names: Optional list of template names to use. If None, all templates will be used.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            List of paths to the generated mockup files
        """
        # Select templates to use based on aspect ratio
        templates_to_use = self.select_templates(template_names, aspect_ratio)

        mockup_paths = []
        successful_templates = 0
        total_templates = len(templates_to_use)

        # Check if the image_path is a URL or a local file path
        if image_path.startswith(("http://", "https://")):
            # It's already a URL, use it directly
            image_url = image_path
            print(f"Using provided image URL: {image_url}")
        else:
            # It's a local file path, we need to upload it
            try:
                image_url = self._upload_image(image_path)
                print(f"Image uploaded successfully. Using URL: {image_url}")
            except Exception as e:
                print(f"Failed to upload image: {str(e)}")
                print("Falling back to sandbox image for testing purposes.")
                image_url = "https://app-dynamicmockups-production.s3.eu-central-1.amazonaws.com/static/api_sandbox_icon.png"

        # Generate mockups for each template
        print(
            f"\nGenerating {total_templates} different mockups for aspect ratio: {aspect_ratio or 'default'}..."
        )

        for template_name, uuids in templates_to_use.items():
            try:
                print(
                    f"\nProcessing template {successful_templates + 1}/{total_templates}: {template_name}"
                )

                # Prepare the mockup request data
                data = {
                    "mockup_uuid": uuids["mockup_uuid"],
                    "smart_objects": [
                        {
                            "uuid": uuids["smart_object_uuid"],
                            "asset": {"url": image_url},
                            "position": {
                                "x": 0.5,  # Center horizontally (0.5 = 50%)
                                "y": 0.5,  # Center vertically (0.5 = 50%)
                                "scale": 1.0,  # Maintain original scale
                                "rotation": 0  # No rotation
                            }
                        }
                    ],
                }

                print(f"Making API request to {self._base_url}/renders")

                # Generate the mockup
                response = requests.post(
                    f"{self._base_url}/renders",
                    headers=self._get_headers(),
                    json=data,
                    timeout=30,  # Add timeout to prevent hanging
                )

                # Handle unsuccessful responses
                if response.status_code != 200:
                    self._handle_error_response(response, template_name)
                    print(f"✗ Failed to generate mockup for template: {template_name}")
                    continue

                # Parse the response
                try:
                    result = response.json()
                except Exception as e:
                    print(f"✗ Failed to parse JSON response: {str(e)}")
                    continue

                if isinstance(result, dict):
                    if "data" not in result or "export_path" not in result["data"]:
                        print("✗ Error: Response does not contain export_path")
                        continue

                    mockup_url = result["data"]["export_path"]
                    print(f"Mockup URL received: {mockup_url}")
                else:
                    print("✗ Error: Response is not a dictionary")
                    continue

                # Download mockup
                print(f"Downloading mockup for {template_name}...")
                mockup_response = requests.get(mockup_url)
                if mockup_response.status_code != 200:
                    print(
                        f"✗ Download failed with status code: {mockup_response.status_code}"
                    )
                    continue

                output_path = self._output_dir / f"mockup_{template_name}.png"
                with open(output_path, "wb") as f:
                    f.write(mockup_response.content)

                size = output_path.stat().st_size
                print(f"✓ Mockup saved to: {output_path} ({size} bytes)")
                mockup_paths.append(str(output_path))
                successful_templates += 1

            except requests.exceptions.RequestException as e:
                print(f"✗ Network error for template {template_name}: {str(e)}")
                continue
            except Exception as e:
                print(f"✗ Unexpected error for template {template_name}: {str(e)}")
                continue

        print(
            f"\nMockup generation complete: {successful_templates}/{total_templates} templates processed successfully"
        )

        if not mockup_paths:
            raise RuntimeError(
                "Failed to generate any mockups. Please check your API key and template UUIDs."
            )

        if successful_templates < total_templates:
            print(
                f"Warning: Only {successful_templates} out of {total_templates} mockups were generated successfully."
            )

        return mockup_paths

    def run(self, tool_input: str) -> str:
        """
        Run the tool with the given input.

        Args:
            tool_input: Input to the tool, can be a path to an image file or a JSON string with
                        additional parameters like {"image_path": "path/to/image.jpg", "template_names": ["frame-mockup", "wall-art-mockup"]}

        Returns:
            String representation of the result
        """
        try:
            # Check if the input is a JSON string with additional parameters
            try:
                input_data = json.loads(tool_input)
                if isinstance(input_data, dict):
                    image_path = input_data.get("image_path")
                    aspect_ratio = input_data.get("aspect_ratio")
                    template_names = input_data.get("template_names")

                    if not image_path:
                        return "Error: 'image_path' is required in the JSON input"
                    
                    # If template_names is not provided, automatically select based on aspect_ratio
                    if template_names is None and aspect_ratio:
                        print(f"No template_names provided, automatically selecting templates for {aspect_ratio} aspect ratio")
                        if aspect_ratio == "portrait":
                            template_names = list(self._portrait_templates.keys())
                            print(f"Selected portrait templates: {template_names}")
                        elif aspect_ratio == "landscape":
                            template_names = list(self._landscape_templates.keys())
                            print(f"Selected landscape templates: {template_names}")
                        else:
                            template_names = list(self._templates.keys())
                            print(f"Selected default templates: {template_names}")

                    result = self._run(image_path, template_names, aspect_ratio)
                else:
                    # If it's not a dict, treat it as a simple image path
                    result = self._run(tool_input)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a simple image path
                result = self._run(tool_input)

            # Format the result as a string
            if isinstance(result, list):
                return "\n".join(result)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"
