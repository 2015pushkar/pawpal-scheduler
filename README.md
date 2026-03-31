# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
py -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

Beyond the basic greedy scheduler, the logic layer includes four algorithmic improvements:

| Feature | Method | What it does |
|---|---|---|
| **Sort by time** | `Scheduler.sort_by_time(tasks)` | Orders tasks chronologically by `time_of_day` ("HH:MM"). Uses a lambda key so string comparison is inherently chronological. Tasks without a time slot sort to the end. |
| **Filter tasks** | `Scheduler.filter_by_pet(tasks, name)` | Returns only tasks belonging to the named pet. |
| | `Scheduler.filter_by_status(tasks, completed)` | Returns tasks matching the given completion state (done / not done). |
| **Recurring tasks** | `Scheduler.mark_task_complete(task, pet)` | Marks a task complete and automatically creates the next occurrence for `daily` (+1 day) and `weekly` (+7 days) tasks using `timedelta`. Non-recurring tasks are simply marked done. |
| **Conflict detection** | `Scheduler.detect_conflicts(schedule)` | Detects two or more tasks assigned the exact same `time_of_day` and returns warning strings. Uses an O(n) dict lookup rather than an O(n²) nested loop. Note: overlapping durations (e.g., 08:00 + 30 min vs 08:15) are not yet checked — see `reflection.md` section 2b for the tradeoff discussion. |

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
