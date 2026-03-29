# AI Engineering Team

An autonomous multi-agent software engineering team built with [CrewAI](https://crewai.com). Give it a plain-English description of a system you want built, and the crew designs, implements, tests, and writes a UI for it — producing runnable Python code with no human intervention.

---

## What it does

The crew takes a set of requirements and runs a two-phase pipeline:

**Phase 1 — Plan**
A Business Analyst refines the raw requirements, then an Engineering Lead decomposes them into a structured multi-module system design (a typed `SystemDesign` Pydantic object listing every module, class, key methods, and inter-module dependencies).

**Phase 2 — Build**
A Backend Engineer implements each module in topological dependency order. Once all modules are built, a Frontend Engineer writes a Gradio UI and a Test Engineer writes a comprehensive unit-test suite — both with full context of every implemented module.

```
Requirements (plain English)
        │
        ▼
┌─────────────────────┐
│   Business Analyst  │  ──▶  output/requirements_spec.md
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  Engineering Lead   │  ──▶  output/system_design.json
└─────────────────────┘       (structured SystemDesign)
        │
        ▼  (one task per module, dependency-ordered)
┌─────────────────────┐
│  Backend Engineer   │  ──▶  output/module_a.py
│  Backend Engineer   │  ──▶  output/module_b.py
│        ...          │
└─────────────────────┘
        │
        ├──▶ ┌───────────────────────┐
        │    │  Frontend Engineer    │  ──▶  output/app.py
        │    └───────────────────────┘
        │
        └──▶ ┌───────────────────────┐
             │    Test Engineer      │  ──▶  output/test_suite.py
             └───────────────────────┘
```

---

## Agents

| Agent | Model | Responsibility |
|---|---|---|
| **Business Analyst** | gpt-5.4-mini | Refines raw requirements into an unambiguous spec |
| **Engineering Lead** | gpt-5.4-mini | Decomposes the spec into a structured multi-module design |
| **Backend Engineer** | gpt-5.4-mini | Implements each Python module (with Docker code execution) |
| **Frontend Engineer** | gpt-5.4-mini | Writes a Gradio UI that imports from all backend modules |
| **Test Engineer** | gpt-5.4-mini | Writes a full unit-test suite covering all modules |

---

## Architecture

```
src/engineering_team/
├── main.py                  # Entry point — orchestrates the two phases
├── crew.py                  # PlanningCrew (@CrewBase) + BuildCrew (dynamic)
├── models.py                # Pydantic models: ModuleSpec, SystemDesign
├── config/
│   ├── agents.yaml          # Agent role / goal / backstory for all five agents
│   ├── tasks.yaml           # Planning-phase task descriptions (used by PlanningCrew)
│   └── build_tasks.yaml     # Build-phase task templates (used by BuildCrew)
└── tools/
    └── custom_tool.py       # Template for adding custom tools
```

**Why two task config files?**
CrewAI's `@CrewBase` decorator auto-discovers every task in `tasks.yaml` and tries to map each `agent` field to a method on the crew class. `PlanningCrew` only knows about `business_analyst` and `engineering_lead` — if it saw `frontend_engineer` or `test_engineer` in the same file it would crash. Keeping build-phase templates in `build_tasks.yaml` means `@CrewBase` never touches them; `BuildCrew` loads that file manually and fills in the `{placeholder}` slots at runtime.

### Key design: structured output + dynamic task creation

The Engineering Lead produces a `SystemDesign` Pydantic object as structured output:

```python
class ModuleSpec(BaseModel):
    module_name: str        # e.g. "accounts.py"
    class_name: str         # e.g. "Account"
    description: str
    key_methods: list[str]  # method signatures
    dependencies: list[str] # other modules this one depends on

class SystemDesign(BaseModel):
    system_overview: str
    modules: list[ModuleSpec]
```

`BuildCrew` reads this at runtime and constructs one CrewAI `Task` per module, performing a topological sort on `dependencies` so that each module's context tasks are ready before it runs. The Frontend and Test tasks receive every backend task as context, giving them full visibility of the implemented code.

This means the crew adapts to whatever complexity the requirements demand — a 1-module system and a 10-module system run through exactly the same code path.

---

## Example output

Running the included trading platform example (`main.py`) produces:

| Output file | Description |
|---|---|
| `output/requirements_spec.md` | Refined requirements from the Business Analyst |
| `output/system_design.json` | Structured design with all modules listed |
| `output/accounts.py` | Backend module with `Account` class, validation, and transaction history |
| `output/app.py` | Gradio UI — deposit, withdraw, buy/sell shares, view portfolio |
| `output/test_suite.py` | Unit tests covering all methods, edge cases, and error conditions |

The generated `accounts.py` includes a clean exception hierarchy, dataclass-based transaction records, and a `get_share_price()` stub for AAPL, TSLA, and GOOGL — all authored entirely by the agents.

---

## Quickstart

### Prerequisites

- Python 3.10–3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (for safe agent code execution)
- An OpenAI API key

### Install

```bash
git clone https://github.com/your-username/crew-engineering-team.git
cd crew-engineering-team

crewai install   # installs dependencies via uv
# or: pip install -e .
```

### Configure

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
```

### Run

```bash
crewai run
```

Outputs land in the `output/` directory. The first run may take several minutes — the agents reason through design and implementation in sequence.

To run the generated Gradio app:

```bash
cd output
python app.py
```

---

## Customising the requirements

Edit the `requirements` string in [src/engineering_team/main.py](src/engineering_team/main.py):

```python
requirements = """
Your requirements here. Describe what system you want built.
The crew will design the modules, implement them, build a UI, and write tests.
"""
```

That's it — no other changes needed. The Engineering Lead decides how many modules to create and how to structure them.

---

## How the two-phase crew works

### Phase 1 — `PlanningCrew` (`@CrewBase`)

A standard sequential CrewAI crew with two agents and two tasks:

1. `requirements_task` → Business Analyst reads requirements, outputs `requirements_spec.md`
2. `design_task` → Engineering Lead reads the spec, outputs a `SystemDesign` Pydantic object

```python
planning_result = PlanningCrew().crew().kickoff(inputs={'requirements': requirements})
system_design: SystemDesign = planning_result.pydantic
```

### Phase 2 — `BuildCrew` (dynamic)

`BuildCrew` is a plain class (not `@CrewBase`) that receives the `SystemDesign` and assembles the crew at runtime:

```python
build_crew_instance = BuildCrew(system_design=system_design, requirements=requirements)
build_result = build_crew_instance.build_crew().kickoff()
```

Internally, `build_crew()`:
1. Loads task templates from `config/build_tasks.yaml`
2. Topologically sorts modules by their `dependencies` field
3. For each module, fills the `code_task` template with `{module_name}`, `{class_name}`, `{key_methods}` etc. and creates a `Task`
4. Chains dependency tasks via CrewAI's `context` parameter
5. Fills `frontend_task` and `test_task` templates with a `{module_summary}` listing all modules, then appends them with all backend tasks as context

---

## Project structure

```
crew-engineering-team/
├── src/
│   └── engineering_team/
│       ├── main.py
│       ├── crew.py
│       ├── models.py
│       ├── config/
│       │   ├── agents.yaml
│       │   ├── tasks.yaml           # planning tasks only
│       │   └── build_tasks.yaml     # build-phase templates
│       └── tools/
│           └── custom_tool.py
├── output/            # Generated code lands here (git-ignored)
├── knowledge/
│   └── user_preference.txt
├── pyproject.toml
└── .env               # API keys (never committed)
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `crewai[tools]>=0.108.0` | Multi-agent framework |
| `gradio>=5.22.0` | Generated UI runtime |
| `litellm<1.82.6` | LLM abstraction layer |
| `pydantic` | Structured agent outputs |

---

## Extending the crew

A few natural next steps:

- **Add a DevOps agent** — generates a `Dockerfile` and `docker-compose.yml` for the produced system
- **Add a Documentation agent** — writes API docs from the implemented modules
- **Swap models per agent** — use a more capable model for the Engineering Lead's structured output and a faster/cheaper one for boilerplate tasks
- **Add tools** — give the Backend Engineer a linter or file-search tool so it can self-correct
- **Interactive requirements** — prompt the user at runtime instead of hardcoding requirements in `main.py`
