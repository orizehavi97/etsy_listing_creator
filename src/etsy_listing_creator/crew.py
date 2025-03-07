import os
from pathlib import Path
from typing import Dict, Any
import json

import yaml
from crewai import Agent, Task, Crew
from dotenv import load_dotenv

from .tools import (
    ReplicateTool,  # New Replicate-based image generator
    ImageProcessingTool,
    DynamicMockupTool,
    JsonSaveTool,
    FileOrganizerTool,
)


class EtsyListingCreator:
    def __init__(self):
        load_dotenv()
        self.config_dir = Path(__file__).parent / "config"
        self.config = {}

        # Try to load config.yaml if it exists
        config_path = self.config_dir / "config.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)

        self.agents = self._load_agents()
        self.tasks = self._load_tasks()

    def _load_agents(self) -> Dict[str, Agent]:
        """Load agent configurations and create Agent instances."""
        with open(self.config_dir / "agents.yaml", "r") as f:
            agents_config = yaml.safe_load(f)

        agents = {}
        tools = {
            "idea_generator": [JsonSaveTool()],
            "image_generator": [
                ReplicateTool()
            ],  # Using Replicate instead of StabilityAI
            # Use ImageProcessingTool for image processing
            "image_processor": [ImageProcessingTool()],
            "mockup_generator": [DynamicMockupTool()],
            "seo_researcher": [JsonSaveTool()],
            "listing_creator": [JsonSaveTool(), FileOrganizerTool()],
        }

        for agent_id, config in agents_config.items():
            agents[agent_id] = Agent(
                role=config["role"],
                goal=config["goal"],
                backstory=config["backstory"],
                tools=tools.get(agent_id, []),
                verbose=True,
            )

        return agents

    def _load_tasks(self) -> Dict[str, Task]:
        """Load task configurations and create Task instances."""
        with open(self.config_dir / "tasks.yaml", "r") as f:
            tasks_config = yaml.safe_load(f)

        tasks = {}
        for task_id, config in tasks_config.items():
            tasks[task_id] = Task(
                description=config["description"],
                expected_output=config["expected_output"],
                agent=self.agents[config["agent"]],
            )

        # Set up task dependencies to ensure proper data flow
        # The prompt engineer should use the output from the idea generator
        if "create_prompt" in tasks and "generate_concept" in tasks:
            tasks["create_prompt"].context = [tasks["generate_concept"]]

        # The image generator should use the output from the prompt engineer
        if "generate_image" in tasks and "create_prompt" in tasks:
            tasks["generate_image"].context = [tasks["create_prompt"]]

        # The mockup generator should use the output from the image generator
        if "create_mockups" in tasks and "generate_image" in tasks:
            tasks["create_mockups"].context = [tasks["generate_image"]]

        # If image processor is enabled, it should use the output from the image generator
        if "process_image" in tasks and "generate_image" in tasks:
            tasks["process_image"].context = [tasks["generate_image"]]

        # The listing creator should use outputs from all previous tasks
        if "create_listing" in tasks:
            context_tasks = []
            for task_id in [
                "generate_concept",
                "create_prompt",
                "generate_image",
                "research_seo",
                "process_image",
                "create_mockups",
            ]:
                if task_id in tasks:
                    context_tasks.append(tasks[task_id])
            tasks["create_listing"].context = context_tasks

        return tasks

    def create_listing(self, concept: str = None) -> Dict[str, Any]:
        """Create a complete Etsy listing."""
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            verbose=True,
        )

        # If no concept is provided, the idea_generator will create one
        if concept:
            self.tasks["generate_concept"].context = (
                f"Use this concept as a starting point: {concept}"
            )

        # Ensure the output directory exists
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Ensuring output directory exists: {output_dir}")

        # Run the crew
        print("Starting the crew workflow...")
        result = crew.kickoff()
        print(f"Crew workflow completed with result: {result}")

        # Check if the result contains a path to the organized directory
        if isinstance(result, str):
            # Handle both old format (direct path to listing.json) and new format (directory path)
            if "output/listing.json" in result:
                json_path = result
                print(f"Listing saved to: {json_path}")
            elif "listing_" in result and "/metadata/listing.json" not in result:
                # This is likely a directory path from the FileOrganizerTool
                json_path = os.path.join(result, "metadata", "listing.json")
                print(f"Listing directory created at: {result}")
                print(f"Listing JSON expected at: {json_path}")
            else:
                # This might be a full path to the listing.json in the new structure
                json_path = result
                print(f"Listing saved to: {json_path}")

            # Optionally, load and return the JSON data
            try:
                if os.path.exists(json_path):
                    print(f"Loading JSON data from: {json_path}")
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)
                    return json_data
                else:
                    print(f"Warning: JSON file not found at {json_path}")
                    
                    # Check if the concept and SEO files were created
                    concept_path = os.path.join("output", "concept_data.json")
                    seo_path = os.path.join("output", "seo_data.json")
                    
                    if os.path.exists(concept_path):
                        print(f"Concept file exists at: {concept_path}")
                    else:
                        print(f"Warning: Concept file not found at {concept_path}")
                        
                    if os.path.exists(seo_path):
                        print(f"SEO file exists at: {seo_path}")
                    else:
                        print(f"Warning: SEO file not found at {seo_path}")
            except Exception as e:
                print(f"Warning: Could not load the saved JSON file: {str(e)}")

        return result


if __name__ == "__main__":
    creator = EtsyListingCreator()
    result = creator.create_listing()
    print("Listing created successfully!")
