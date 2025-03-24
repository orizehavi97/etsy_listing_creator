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
        task_dependencies = {
            "create_prompt": ["generate_concept"],
            "generate_image": ["create_prompt"],
            "process_image": ["generate_image"],
            "create_mockups": ["generate_image"],
            "research_seo": ["create_prompt"],
            "create_listing": [
                "generate_concept",
                "create_prompt",
                "generate_image",
                "research_seo",
                "process_image",
                "create_mockups"
            ]
        }

        # Apply dependencies
        for task_id, dependencies in task_dependencies.items():
            if task_id in tasks:
                tasks[task_id].context = [tasks[dep] for dep in dependencies if dep in tasks]

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

        # Handle the result based on its type
        if isinstance(result, dict):
            # If result is already a dictionary, return it
            return result
        elif isinstance(result, str):
            # Handle string results (file paths)
            if "output/listing.json" in result:
                json_path = result
            elif "listing_" in result and "/metadata/listing.json" not in result:
                json_path = os.path.join(result, "metadata", "listing.json")
            else:
                json_path = result

            # Load and return the JSON data if it exists
            try:
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                else:
                    print(f"Warning: JSON file not found at {json_path}")
                    return {"status": "error", "message": "Listing JSON not found"}
            except Exception as e:
                print(f"Error loading JSON file: {str(e)}")
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": "Unexpected result type"}


if __name__ == "__main__":
    count = int(input("How many listings do you want to create? "))
    for i in range(count):
        creator = EtsyListingCreator()
        result = creator.create_listing()
        print(f"Listing {i+1} created successfully!")
    print("All listings created successfully!")
