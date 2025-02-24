import os
from pathlib import Path
from typing import Dict, Any

import yaml
from crewai import Agent, Task, Crew
from dotenv import load_dotenv

from .tools import (
    StabilityAITool,
    ClaidImageTool,
    DynamicMockupTool,
    SemrushTool,
)

class EtsyListingCreator:
    def __init__(self):
        load_dotenv()
        self.config_dir = Path(__file__).parent / "config"
        self.agents = self._load_agents()
        self.tasks = self._load_tasks()

    def _load_agents(self) -> Dict[str, Agent]:
        """Load agent configurations and create Agent instances."""
        with open(self.config_dir / "agents.yaml", "r") as f:
            agents_config = yaml.safe_load(f)

        agents = {}
        tools = {
            "image_generator": [StabilityAITool()],
            "image_processor": [ClaidImageTool()],
            "mockup_generator": [DynamicMockupTool()],
            #"seo_researcher": [SemrushTool()],
        }

        for agent_id, config in agents_config.items():
            agents[agent_id] = Agent(
                role=config["role"],
                goal=config["goal"],
                backstory=config["backstory"],
                tools=tools.get(agent_id, []),
                verbose=True
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
        
        return tasks

    def create_listing(self, concept: str = None) -> Dict[str, Any]:
        """Create a complete Etsy listing."""
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            verbose=True
        )

        # If no concept is provided, the idea_generator will create one
        if concept:
            self.tasks["generate_concept"].context = f"Use this concept as a starting point: {concept}"

        result = crew.kickoff()
        return result

if __name__ == "__main__":
    creator = EtsyListingCreator()
    result = creator.create_listing()
    print("Listing created successfully!") 