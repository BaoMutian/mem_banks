#!/usr/bin/env python3
"""
Generate SFT training data from ALFWorld evaluation results.

This script reads memory (jsonl) and results (json) files from a directory,
then generates message format (system, user, assistant) for SFT training.

Usage:
    python generate_sft_data.py /path/to/directory [--output output.jsonl]
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


# ========== Prompt Constants (from system.py and few_shot.py) ==========

FEW_SHOT_EXAMPLES = """Example 1: 

You are in the middle of a room. Looking quickly around you, you see a bed 1, a desk 1, a desklamp 1, a drawer 1.
Your task is to: examine the alarmclock with the desklamp.

Think: I need to find an alarm clock and examine it under the desk lamp. Let me check the desk first.
Action: go to desk 1

> go to desk 1
On the desk 1, you see an alarmclock 1, a pen 1.

Think: Found the alarm clock. Let me pick it up.
Action: take alarmclock 1 from desk 1

> take alarmclock 1 from desk 1
You pick up the alarmclock 1 from the desk 1.

Think: Now I have the alarm clock. I need to use the desk lamp to illuminate and examine it.
Action: use desklamp 1

> use desklamp 1
You turn on the desklamp 1.
Task completed!

---

Example 2: 

You are in the middle of a room. Looking quickly around you, you see a cabinet 1, a coffeemachine 1, a countertop 1, a fridge 1, a sinkbasin 1.
Your task is to: clean some mug and put it in coffeemachine.

Think: I need to find a mug, clean it in the sink, then put it in the coffee machine. Let me look for a mug.
Action: go to countertop 1

> go to countertop 1
On the countertop 1, you see a mug 1, a knife 1.

Think: I found a mug. Let me pick it up.
Action: take mug 1 from countertop 1

> take mug 1 from countertop 1
You pick up the mug 1 from the countertop 1.

Think: Now I need to clean the mug in the sink.
Action: go to sinkbasin 1

> go to sinkbasin 1
On the sinkbasin 1, you see nothing.

Think: I'm at the sink. Let me clean the mug.
Action: clean mug 1 with sinkbasin 1

> clean mug 1 with sinkbasin 1
You clean the mug 1 using the sinkbasin 1.

Think: The mug is clean. Now I need to put it in the coffee machine.
Action: go to coffeemachine 1

> go to coffeemachine 1
On the coffeemachine 1, you see nothing.

Think: I'm at the coffee machine. Let me put the clean mug here.
Action: move mug 1 to coffeemachine 1

> move mug 1 to coffeemachine 1
You put the mug 1 in/on the coffeemachine 1.
Task completed!
"""

_SYSTEM_PROMPT_BASE = """You are an intelligent agent operating in a household environment. Your goal is to complete tasks by interacting with objects and navigating through rooms.

==================================================
ENVIRONMENT RULES
==================================================
1. You can only carry ONE object at a time
2. Use exact object names with numbers (e.g., "apple 1", "fridge 1")

==================================================
AVAILABLE COMMANDS
==================================================
Navigation:
  - look                          : View current surroundings
  - go to [receptacle]            : Move to a location (e.g., "go to fridge 1")

Object Manipulation:
  - take [object] from [receptacle] : Pick up an object (e.g., "take apple 1 from fridge 1")
  - move [object] to [receptacle]   : Place object (e.g., "move apple 1 to fridge 1")
  - open [receptacle]               : Open a container (e.g., "open fridge 1")
  - close [receptacle]              : Close a container

Object Processing:
  - heat [object] with [receptacle] : Heat with microwave (e.g., "heat egg 1 with microwave 1")
  - cool [object] with [receptacle] : Cool with fridge (e.g., "cool apple 1 with fridge 1")
  - clean [object] with [receptacle]: Clean with sink (e.g., "clean mug 1 with sinkbasin 1")
  - use [object]                    : Use/toggle object (e.g., "use desklamp 1")

Utility:
  - inventory                      : Check what you're carrying
  - examine [object]               : Look at object details
  - check valid actions            : List all currently valid actions

==================================================
OUTPUT FORMAT
==================================================
You MUST respond in EXACTLY this format:

Think: <your reasoning about the current situation and what to do next>

Action: <exact command from the list above>

IMPORTANT:
- Always include both "Think:" and "Action:" sections
- The action must be a valid command with exact object/receptacle names
- If stuck, use "check valid actions" to see available options"""

SYSTEM_PROMPT_WITH_EXAMPLES = _SYSTEM_PROMPT_BASE + """

==================================================
EXAMPLE DEMONSTRATIONS
==================================================
The following examples show how to complete various tasks:

""" + FEW_SHOT_EXAMPLES


# ========== Data Classes ==========

@dataclass
class MemoryItem:
    """Memory item from extracted insights."""
    title: str
    description: str
    content: str


@dataclass
class RetrievedMemory:
    """Retrieved memory for a task."""
    memory_id: str
    similarity: float
    query: str
    is_success: bool
    trajectory: List[Dict[str, str]]
    memory_items: List[MemoryItem]


# ========== Helper Functions ==========

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL file and return list of dictionaries."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON file and return dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_files_in_directory(directory: str) -> Tuple[List[str], List[str]]:
    """Find all .jsonl (memory) and .json (results) files in directory.

    Note: Only .jsonl files containing 'mem' in the filename are considered as memory files.
    This avoids accidentally loading output files like sft_data.jsonl as memory.
    """
    jsonl_files = []
    json_files = []

    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if file.endswith('.jsonl'):
            # Only consider files with 'mem' in name as memory files
            if 'mem' in file.lower():
                jsonl_files.append(file_path)
        elif file.endswith('.json'):
            # Only consider files with 'result' in name as results files
            if 'result' in file.lower():
                json_files.append(file_path)

    return jsonl_files, json_files


def format_trajectory_for_memory(trajectory: List[Dict[str, str]], max_show: int = 6) -> str:
    """Format trajectory for memory display (abbreviated)."""
    if not trajectory:
        return "(empty)"

    lines = []

    if len(trajectory) <= max_show:
        for step in trajectory:
            action = step.get("action", "")
            lines.append(f"  > {action}")
    else:
        # Show first 3 and last 3
        for step in trajectory[:3]:
            action = step.get("action", "")
            lines.append(f"  > {action}")
        lines.append(f"  ... ({len(trajectory) - 6} more steps) ...")
        for step in trajectory[-3:]:
            action = step.get("action", "")
            lines.append(f"  > {action}")

    return "\n".join(lines)


def format_memory_items(memory_items: List[MemoryItem]) -> str:
    """Format memory items for display."""
    if not memory_items:
        return ""

    lines = ["  Key Insights:"]
    for item in memory_items:
        lines.append(f"    - {item.title}: {item.description}")
        if item.content:
            lines.append(f"      {item.content}")

    return "\n".join(lines)


def build_memory_section(retrieved_memories: List[RetrievedMemory]) -> str:
    """Build the memory section for system prompt."""
    if not retrieved_memories:
        return ""

    parts = [
        "",
        "==================================================",
        "RELEVANT EXPERIENCE FROM SIMILAR TASKS",
        "==================================================",
        "Below are key insights from past interactions that may help with your current task.",
        "Use them as reference when relevant, but adapt to the specific situation.",
        "",
    ]

    for i, rm in enumerate(retrieved_memories, 1):
        parts.append(
            f"[Experience #{i}] (Similarity: {rm.similarity:.2f})")

        # Only add memory items (key insights), skip goal and trajectory
        if rm.memory_items:
            for item in rm.memory_items:
                parts.append(f"  • {item.title}: {item.description}")
                if item.content:
                    parts.append(f"    {item.content}")

        parts.append("")

    return "\n".join(parts)


def get_system_prompt_with_memory(
    use_few_shot: bool = True,
    retrieved_memories: Optional[List[RetrievedMemory]] = None,
) -> str:
    """Get system prompt with optional few-shot examples and retrieved memories."""
    if use_few_shot:
        base_prompt = SYSTEM_PROMPT_WITH_EXAMPLES
    else:
        base_prompt = _SYSTEM_PROMPT_BASE

    if not retrieved_memories:
        return base_prompt

    memory_section = build_memory_section(retrieved_memories)

    # Insert memory section before OUTPUT FORMAT section
    output_format_marker = "==================================================\nOUTPUT FORMAT"

    if output_format_marker in base_prompt:
        idx = base_prompt.find(output_format_marker)
        return base_prompt[:idx] + memory_section + "\n" + base_prompt[idx:]
    else:
        return base_prompt + memory_section


def build_user_prompt(
    task_description: str,
    history: List[Tuple[str, str]],
    current_observation: str,
    history_length: int = 10,
) -> str:
    """Build user prompt with task, history, and current observation."""
    parts = []

    # Add current task
    parts.append("==================================================")
    parts.append("YOUR CURRENT TASK")
    parts.append("==================================================")
    parts.append(f"Goal: {task_description}")
    parts.append("")
    parts.append("Hints:")
    parts.append("  - Type 'check valid actions' if you're unsure what to do")
    parts.append("  - Type 'inventory' to check what you're carrying")
    parts.append("  - Type 'look' to observe your surroundings")
    parts.append("")

    # Add recent history
    parts.append("==================================================")
    parts.append("RECENT HISTORY")
    parts.append("==================================================")

    # Limit history length
    recent_history = history[-history_length:] if len(
        history) > history_length else history

    if recent_history:
        for action, observation in recent_history:
            parts.append(f"Action: {action}")
            parts.append(f"Observation: {observation}")
            parts.append("")

    # Add current observation
    parts.append("Current Observation:")
    parts.append(current_observation)
    parts.append("")

    # Reminder
    parts.append("==================================================")
    parts.append("YOUR TURN")
    parts.append("==================================================")
    parts.append(
        "Based on the task goal and current observation, decide your next action.")
    parts.append("Remember to use the exact format: Think: ... Action: ...")

    return "\n".join(parts)


def extract_task_description(initial_observation: str) -> str:
    """Extract task description from initial observation."""
    lines = initial_observation.split("\n")
    for line in lines:
        if "your task is to" in line.lower():
            return line.strip()
    return initial_observation.strip()


# ========== Main Processing Functions ==========

def load_memory_bank(jsonl_files: List[str]) -> Dict[str, Dict[str, Any]]:
    """Load memory bank from JSONL files, indexed by memory_id."""
    memory_bank = {}

    for jsonl_file in jsonl_files:
        print(f"Loading memory from: {jsonl_file}")
        memories = load_jsonl(jsonl_file)
        for mem in memories:
            memory_id = mem.get("memory_id", "")
            if memory_id:
                memory_bank[memory_id] = mem

    print(f"Loaded {len(memory_bank)} memories from {len(jsonl_files)} file(s)")
    return memory_bank


def get_retrieved_memories(
    used_memories: List[Dict[str, Any]],
    memory_bank: Dict[str, Dict[str, Any]]
) -> List[RetrievedMemory]:
    """Get RetrievedMemory objects from used_memories references."""
    retrieved = []

    for mem_ref in used_memories:
        memory_id = mem_ref.get("memory_id", "")
        similarity = mem_ref.get("similarity", 0.0)

        if memory_id in memory_bank:
            mem_data = memory_bank[memory_id]

            # Parse memory items
            memory_items = []
            for item in mem_data.get("memory_items", []):
                memory_items.append(MemoryItem(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    content=item.get("content", ""),
                ))

            retrieved.append(RetrievedMemory(
                memory_id=memory_id,
                similarity=similarity,
                query=mem_data.get("query", ""),
                is_success=mem_data.get("is_success", False),
                trajectory=mem_data.get("trajectory", []),
                memory_items=memory_items,
            ))

    return retrieved


def generate_sft_samples(
    result: Dict[str, Any],
    memory_bank: Dict[str, Dict[str, Any]],
    use_few_shot: bool = True,
    history_length: int = 10,
    only_success: bool = False,
) -> List[Dict[str, Any]]:
    """
    Generate SFT training samples from a single result instance.

    Each step in the trajectory generates one training sample with:
    - system: System prompt with memory (if available)
    - user: User prompt with history and current observation
    - assistant: Think + Action response

    Returns:
        List of training samples, each containing 'messages' key.
    """
    # Skip failed cases if only_success is True
    if only_success and not result.get("success", False):
        return []

    samples = []

    # Extract basic info
    goal = result.get("goal", "")
    actions = result.get("actions", [])
    observations = result.get("observations", [])
    thoughts = result.get("thoughts", [])
    used_memories = result.get("used_memories", [])
    game_id = result.get("game_id", "")
    success = result.get("success", False)

    # Get retrieved memories
    retrieved_memories = get_retrieved_memories(used_memories, memory_bank)

    # Build system prompt (same for all steps in this task)
    system_prompt = get_system_prompt_with_memory(
        use_few_shot=use_few_shot,
        retrieved_memories=retrieved_memories,
    )

    # Extract task description from goal or first observation
    if goal:
        task_description = goal
    elif observations:
        task_description = extract_task_description(observations[0])
    else:
        task_description = "Complete the task."

    # Build history as list of (action, observation) tuples
    history: List[Tuple[str, str]] = []

    # Generate samples for each step
    for step_idx in range(len(actions)):
        action = actions[step_idx]

        # Current observation (shift by 1 since observations[0] is initial)
        if step_idx < len(observations):
            current_obs = observations[step_idx]
        else:
            current_obs = ""

        # Get thought for this step
        if step_idx < len(thoughts):
            thought = thoughts[step_idx]
        else:
            thought = ""

        # Build user prompt
        user_prompt = build_user_prompt(
            task_description=task_description,
            history=history,
            current_observation=current_obs,
            history_length=history_length,
        )

        # Build assistant response
        assistant_response = f"Think: {thought}\n\nAction: {action}"

        # Create sample
        sample = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response},
            ],
            "metadata": {
                "game_id": game_id,
                "step": step_idx,
                "total_steps": len(actions),
                "success": success,
                "action": action,
                "has_memory": len(retrieved_memories) > 0,
            }
        }

        samples.append(sample)

        # Update history for next step
        # Get next observation for this action
        if step_idx + 1 < len(observations):
            next_obs = observations[step_idx + 1]
        else:
            next_obs = ""

        history.append((action, next_obs))

    return samples


def process_results_file(
    results_file: str,
    memory_bank: Dict[str, Dict[str, Any]],
    use_few_shot: bool = True,
    history_length: int = 10,
    only_success: bool = False,
) -> List[Dict[str, Any]]:
    """Process a single results file and generate all SFT samples."""
    print(f"Processing results file: {results_file}")

    data = load_json(results_file)
    results = data.get("results", [])

    all_samples = []
    success_count = 0
    failed_count = 0

    for result in results:
        if result.get("success", False):
            success_count += 1
        else:
            failed_count += 1

        samples = generate_sft_samples(
            result=result,
            memory_bank=memory_bank,
            use_few_shot=use_few_shot,
            history_length=history_length,
            only_success=only_success,
        )
        all_samples.extend(samples)

    print(
        f"  - Total instances: {len(results)} ({success_count} success, {failed_count} failed)")
    print(f"  - Generated samples: {len(all_samples)}")

    return all_samples


def main():
    parser = argparse.ArgumentParser(
        description="Generate SFT training data from ALFWorld evaluation results."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing .jsonl (memory) and .json (results) files",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: <directory>/sft_data.jsonl)",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Disable few-shot examples in system prompt",
    )
    parser.add_argument(
        "--history-length",
        type=int,
        default=10,
        help="Number of recent history entries to include (default: 10)",
    )
    parser.add_argument(
        "--only-success",
        action="store_true",
        help="Only generate samples from successful episodes",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory retrieval (ignore .jsonl files)",
    )

    args = parser.parse_args()

    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a valid directory")
        sys.exit(1)

    # Find files
    jsonl_files, json_files = find_files_in_directory(args.directory)

    if not json_files:
        print(f"Error: No .json files found in {args.directory}")
        sys.exit(1)

    print(
        f"Found {len(jsonl_files)} .jsonl file(s) and {len(json_files)} .json file(s)")

    # Load memory bank
    if args.no_memory:
        memory_bank = {}
        print("Memory disabled, skipping .jsonl files")
    else:
        memory_bank = load_memory_bank(jsonl_files)

    # Process all results files
    all_samples = []
    for json_file in json_files:
        samples = process_results_file(
            results_file=json_file,
            memory_bank=memory_bank,
            use_few_shot=not args.no_few_shot,
            history_length=args.history_length,
            only_success=args.only_success,
        )
        all_samples.extend(samples)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(args.directory, "sft_data.jsonl")

    # Save samples
    print(f"\nSaving {len(all_samples)} samples to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print("Done!")

    # Print statistics
    success_samples = sum(1 for s in all_samples if s["metadata"]["success"])
    failed_samples = len(all_samples) - success_samples
    with_memory = sum(1 for s in all_samples if s["metadata"]["has_memory"])

    print("\n=== Statistics ===")
    print(f"Total samples: {len(all_samples)}")
    print(f"  - From successful episodes: {success_samples}")
    print(f"  - From failed episodes: {failed_samples}")
    print(f"  - With memory: {with_memory}")
    print(f"  - Without memory: {len(all_samples) - with_memory}")


if __name__ == "__main__":
    main()
