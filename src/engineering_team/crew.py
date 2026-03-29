import yaml
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from engineering_team.models import ModuleSpec, SystemDesign


gpt_5_mini = LLM(
    model="openai/gpt-5.4-mini",
    additional_drop_params=["stop"]
)

_AGENTS_CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"
_BUILD_TASKS_CONFIG_PATH = Path(__file__).parent / "config" / "build_tasks.yaml"


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Phase 1 — Planning Crew
# ---------------------------------------------------------------------------

@CrewBase
class PlanningCrew():
    """Produces a structured SystemDesign from raw requirements."""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def business_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['business_analyst'],
            llm=gpt_5_mini,
            verbose=True,
        )

    @agent
    def engineering_lead(self) -> Agent:
        return Agent(
            config=self.agents_config['engineering_lead'],
            llm=gpt_5_mini,
            verbose=True,
        )

    @task
    def requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['requirements_task'],
        )

    @task
    def design_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_task'],
            output_pydantic=SystemDesign,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


# ---------------------------------------------------------------------------
# Phase 2 — Build Crew (dynamically assembled from SystemDesign)
# ---------------------------------------------------------------------------

class BuildCrew():
    """Dynamically builds and runs a crew that implements every module in SystemDesign."""

    def __init__(self, system_design: SystemDesign, requirements: str):
        self.system_design = system_design
        self.requirements = requirements

        agents_cfg = _load_yaml(_AGENTS_CONFIG_PATH)
        self._tasks_cfg = _load_yaml(_BUILD_TASKS_CONFIG_PATH)

        # Interpolate {requirements} in agent configs since we're outside @CrewBase
        for key in agents_cfg:
            for field in ('role', 'goal', 'backstory'):
                if field in agents_cfg[key]:
                    agents_cfg[key][field] = agents_cfg[key][field].replace(
                        '{requirements}', requirements
                    )

        self._backend_engineer = Agent(
            role=agents_cfg['backend_engineer']['role'],
            goal=agents_cfg['backend_engineer']['goal'],
            backstory=agents_cfg['backend_engineer']['backstory'],
            llm=gpt_5_mini,
            verbose=True,
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=500,
            max_retry_limit=3,
        )
        self._frontend_engineer = Agent(
            role=agents_cfg['frontend_engineer']['role'],
            goal=agents_cfg['frontend_engineer']['goal'],
            backstory=agents_cfg['frontend_engineer']['backstory'],
            llm=gpt_5_mini,
            verbose=True,
        )
        self._test_engineer = Agent(
            role=agents_cfg['test_engineer']['role'],
            goal=agents_cfg['test_engineer']['goal'],
            backstory=agents_cfg['test_engineer']['backstory'],
            llm=gpt_5_mini,
            verbose=True,
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=500,
            max_retry_limit=3,
        )

    def _sorted_modules(self) -> list[ModuleSpec]:
        """Return modules in topological order (dependencies built first)."""
        module_map = {m.module_name: m for m in self.system_design.modules}
        visited: set[str] = set()
        result: list[ModuleSpec] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            module = module_map.get(name)
            if module is None:
                return
            for dep in module.dependencies:
                visit(dep)
            result.append(module)

        for m in self.system_design.modules:
            visit(m.module_name)

        return result

    def build_crew(self) -> Crew:
        sorted_modules = self._sorted_modules()
        task_map: dict[str, Task] = {}
        backend_tasks: list[Task] = []
        code_cfg = self._tasks_cfg['code_task']

        for module in sorted_modules:
            context_tasks = [task_map[dep] for dep in module.dependencies if dep in task_map]
            key_methods = "\n".join(f"  - {m}" for m in module.key_methods)
            t = Task(
                description=code_cfg['description'].format(
                    module_name=module.module_name,
                    class_name=module.class_name,
                    description=module.description,
                    key_methods=key_methods,
                    requirements=self.requirements,
                ),
                expected_output=code_cfg['expected_output'].format(
                    module_name=module.module_name,
                ),
                agent=self._backend_engineer,
                context=context_tasks if context_tasks else None,
                output_file=code_cfg['output_file'].format(module_name=module.module_name),
            )
            backend_tasks.append(t)
            task_map[module.module_name] = t

        module_summary = "\n".join(
            f"  - {m.module_name}: class {m.class_name} — {m.description}"
            for m in sorted_modules
        )

        fe_cfg = self._tasks_cfg['frontend_task']
        frontend_task = Task(
            description=fe_cfg['description'].format(
                module_summary=module_summary,
                requirements=self.requirements,
            ),
            expected_output=fe_cfg['expected_output'],
            agent=self._frontend_engineer,
            context=backend_tasks,
            output_file=fe_cfg['output_file'],
        )

        test_cfg = self._tasks_cfg['test_task']
        test_task = Task(
            description=test_cfg['description'].format(
                module_summary=module_summary,
                requirements=self.requirements,
            ),
            expected_output=test_cfg['expected_output'],
            agent=self._test_engineer,
            context=backend_tasks,
            output_file=test_cfg['output_file'],
        )

        all_tasks = backend_tasks + [frontend_task, test_task]
        all_agents = [self._backend_engineer, self._frontend_engineer, self._test_engineer]

        return Crew(
            agents=all_agents,
            tasks=all_tasks,
            process=Process.sequential,
            verbose=True,
        )
