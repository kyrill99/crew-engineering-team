#!/usr/bin/env python
import json
import os
import warnings

from engineering_team.crew import BuildCrew, PlanningCrew
from engineering_team.models import SystemDesign

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

requirements = """
A simple account management system for a trading simulation platform.
The system should allow users to create an account, deposit funds, and withdraw funds.
The system should allow users to record that they have bought or sold shares, providing a quantity.
The system should calculate the total value of the user's portfolio, and the profit or loss from the initial deposit.
The system should be able to report the holdings of the user at any point in time.
The system should be able to report the profit or loss of the user at any point in time.
The system should be able to list the transactions that the user has made over time.
The system should prevent the user from withdrawing funds that would leave them with a negative balance, or
 from buying more shares than they can afford, or selling shares that they don't have.
 The system has access to a function get_share_price(symbol) which returns the current price of a share,
 and includes a test implementation that returns fixed prices for AAPL, TSLA, GOOGL.
"""


def run():
    os.makedirs('output', exist_ok=True)

    # ------------------------------------------------------------------
    # Phase 1: Planning — business analyst + engineering lead produce
    # a structured SystemDesign listing all modules to build.
    # ------------------------------------------------------------------
    print("\n=== Phase 1: Planning System Design ===\n")
    planning_result = PlanningCrew().crew().kickoff(inputs={'requirements': requirements})

    system_design: SystemDesign | None = planning_result.pydantic

    # Fall back to parsing raw output if structured output wasn't populated
    if system_design is None:
        print("Structured output not populated — attempting to parse raw JSON...")
        try:
            raw = planning_result.raw.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            system_design = SystemDesign.model_validate(json.loads(raw))
        except Exception as e:
            raise ValueError(f"Planning crew did not produce a valid SystemDesign: {e}") from e

    if not system_design.modules:
        raise ValueError("SystemDesign contains no modules — cannot proceed to build phase.")

    print(f"\n=== System Design: {len(system_design.modules)} module(s) planned ===")
    for m in system_design.modules:
        deps = f" (depends on: {', '.join(m.dependencies)})" if m.dependencies else ""
        print(f"  - {m.module_name}: class {m.class_name}{deps}")

    # Persist the design as JSON for inspection
    with open("output/system_design.json", "w") as f:
        f.write(system_design.model_dump_json(indent=2))
    print("\nSystem design saved to output/system_design.json")

    # ------------------------------------------------------------------
    # Phase 2: Build — one backend task per module, then frontend + tests
    # ------------------------------------------------------------------
    print("\n=== Phase 2: Building System ===\n")
    build_result = BuildCrew(system_design=system_design, requirements=requirements).build_crew().kickoff()

    print("\n=== Build Complete ===")
    print(build_result.raw)


if __name__ == "__main__":
    run()
