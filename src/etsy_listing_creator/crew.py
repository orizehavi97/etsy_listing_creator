import os
from pathlib import Path
from typing import Dict, Any
import json

import yaml
from crewai import Agent, Task, Crew
from dotenv import load_dotenv

from .tools import (
    StabilityAITool,
    ClaidImageTool,
    DynamicMockupTool,
    SemrushTool,
    JsonSaveTool,
    PrintPreparationTool,
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
            "image_generator": [StabilityAITool()],
            # Always use local processing with PrintPreparationTool instead of Claid.ai API
            "image_processor": [ClaidImageTool(use_local_processing=True)],
            "mockup_generator": [DynamicMockupTool()],
            # "seo_researcher": [SemrushTool()],
            "listing_creator": [JsonSaveTool()],
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

        result = crew.kickoff()

        # Check if the result contains a path to the JSON file
        if isinstance(result, str) and "output/listing.json" in result:
            print(f"Listing saved to: {result}")

            # Optionally, load and return the JSON data
            try:
                with open(result, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                return json_data
            except Exception as e:
                print(f"Warning: Could not load the saved JSON file: {str(e)}")

        return result


if __name__ == "__main__":
    creator = EtsyListingCreator()
    result = creator.create_listing()
    print("Listing created successfully!")
