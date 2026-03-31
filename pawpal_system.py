"""
pawpal_system.py
Logic layer for PawPal+. Contains all backend classes.

Retrieval flow:
    Scheduler -> Owner.get_all_tasks() -> [Pet.get_tasks() for pet in owner.pets]
"""

from __future__ import annotations
from datetime import date, timedelta

# Maps priority labels to sort order (lower number = higher priority).
PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}
VALID_PRIORITIES: tuple[str, ...] = ("low", "medium", "high")
VALID_FREQUENCIES: tuple[str, ...] = ("daily", "weekly", "as-needed")

# Days to add for each recurrence frequency.
_RECUR_DAYS: dict[str, int] = {"daily": 1, "weekly": 7}


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task:
    """Represents a single pet care activity with a completion status."""

    def __init__(
        self,
        title: str,
        duration_minutes: int,
        priority: str,
        frequency: str = "daily",
        category: str = "general",
        time_of_day: str = "",
        due_date: date | None = None,
    ):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority          # "low", "medium", or "high"
        self.frequency = frequency        # "daily", "weekly", or "as-needed"
        self.category = category          # e.g. "exercise", "feeding", "medical"
        self.time_of_day = time_of_day    # optional "HH:MM" string; "" means unscheduled
        self.due_date: date = due_date or date.today()
        self.completed: bool = False
        self.reason_skipped: str = ""     # populated by Scheduler when a task is dropped

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def is_valid(self) -> bool:
        """Return True if duration is positive and priority is a recognised value."""
        return self.duration_minutes > 0 and self.priority in VALID_PRIORITIES

    def to_dict(self) -> dict:
        """Return a plain-dict representation of the task (useful for Streamlit tables)."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "frequency": self.frequency,
            "category": self.category,
            "time_of_day": self.time_of_day,
            "due_date": str(self.due_date),
            "completed": self.completed,
        }


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

class Pet:
    """Represents a pet and owns its list of care tasks."""

    def __init__(self, name: str, species: str, age: int, special_needs: list[str] | None = None):
        self.name = name
        self.species = species            # e.g. "dog", "cat", "other"
        self.age = age                    # in years
        self.special_needs: list[str] = special_needs or []
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a valid task to this pet's task list; raise ValueError for invalid tasks."""
        if not task.is_valid():
            raise ValueError(f"Task '{task.title}' is invalid (check duration and priority).")
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove the first task whose title matches; do nothing if not found."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)

    def get_info(self) -> str:
        """Return a one-line summary string of the pet's name, species, and age."""
        return f"{self.name} ({self.species}, {self.age}yr)"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """Manages one or more pets and exposes all their tasks as a flat list."""

    def __init__(self, name: str, available_minutes_per_day: int, preferences: list[str] | None = None):
        self.name = name
        self.available_minutes_per_day = available_minutes_per_day
        self.preferences: list[str] = preferences or []
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove the first pet whose name matches; do nothing if not found."""
        self.pets = [p for p in self.pets if p.name != name]

    def get_all_tasks(self) -> list[Task]:
        """Return a flat list of every task across all of the owner's pets."""
        return [task for pet in self.pets for task in pet.get_tasks()]

    def get_available_time(self) -> int:
        """Return the number of minutes available for pet care today."""
        return self.available_minutes_per_day

    def update_preferences(self, prefs: list[str]) -> None:
        """Replace the owner's preference list with the provided list."""
        self.preferences = prefs


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

class Schedule:
    """Represents a single day's ordered care plan produced by the Scheduler."""

    def __init__(self):
        self.tasks: list[Task] = []           # tasks that fit and will be done
        self.skipped_tasks: list[Task] = []   # tasks dropped due to constraints

    def add_task(self, task: Task) -> None:
        """Append a task to the scheduled list."""
        self.tasks.append(task)

    def get_total_duration(self) -> int:
        """Compute and return total minutes across all scheduled tasks."""
        return sum(t.duration_minutes for t in self.tasks)

    def get_summary(self) -> str:
        """Return a formatted multi-line string of scheduled and skipped tasks."""
        lines = [f"  [x] {t.title} ({t.duration_minutes} min)" for t in self.tasks]
        if self.skipped_tasks:
            lines.append("  Skipped:")
            lines += [f"  [-] {t.title} - {t.reason_skipped}" for t in self.skipped_tasks]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Scheduling engine -- retrieves tasks from the Owner's pets and produces a daily Schedule.

    Retrieval path:
        self.owner.get_all_tasks()
            -> iterates owner.pets
            -> calls pet.get_tasks() on each
            -> returns one flat list for the scheduling algorithm
    """

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Delegate to owner.get_all_tasks() to collect every task across all pets."""
        return self.owner.get_all_tasks()

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by time_of_day in ascending HH:MM order.

        Tasks without a time_of_day ("") sort to the end.
        Uses a lambda key so HH:MM strings compare correctly as-is
        (lexicographic order of zero-padded HH:MM equals chronological order).
        Tasks without a set time get "99:99" as their sort key so they
        fall after all timed tasks -- no extra if-branch needed inside the loop.
        """
        return sorted(tasks, key=lambda t: t.time_of_day if t.time_of_day else "99:99")

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_by_pet(self, tasks: list[Task], pet_name: str) -> list[Task]:
        """Return only the tasks that belong to the pet with the given name."""
        pet = next((p for p in self.owner.pets if p.name == pet_name), None)
        if pet is None:
            return []
        pet_task_ids = {id(t) for t in pet.tasks}
        return [t for t in tasks if id(t) in pet_task_ids]

    def filter_by_status(self, tasks: list[Task], completed: bool) -> list[Task]:
        """Return only tasks whose completed flag matches the given value."""
        return [t for t in tasks if t.completed == completed]

    # ------------------------------------------------------------------
    # Recurring tasks
    # ------------------------------------------------------------------

    def mark_task_complete(self, task: Task, pet: Pet) -> Task | None:
        """Mark a task complete and, for recurring tasks, add the next occurrence to the pet.

        For 'daily'  frequency: next due_date = today + 1 day.
        For 'weekly' frequency: next due_date = today + 7 days.
        For 'as-needed': no follow-up task is created.
        Returns the newly created follow-up Task, or None if non-recurring.

        This keeps mark_complete() on Task simple (just flips the flag) and
        puts the recurrence logic here in the Scheduler where it belongs.
        """
        task.mark_complete()
        days = _RECUR_DAYS.get(task.frequency)
        if days is None:
            return None
        next_task = Task(
            title=task.title,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            frequency=task.frequency,
            category=task.category,
            time_of_day=task.time_of_day,
            due_date=date.today() + timedelta(days=days),
        )
        pet.add_task(next_task)
        return next_task

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, schedule: Schedule) -> list[str]:
        """Detect tasks scheduled at the exact same time_of_day and return warning strings.

        Strategy: single-pass dict lookup -- O(n) rather than the O(n^2) nested-loop
        alternative.  We trade a small amount of extra memory (the seen dict) for a
        loop that only visits each task once.  Only tasks with a non-empty time_of_day
        are considered; untimed tasks are ignored.

        Tradeoff: this only catches exact HH:MM matches.  Two tasks at "08:00" and
        "08:15" would not be flagged even if the first task runs for 30 minutes and
        physically overlaps the second.  A duration-aware check would require sorting
        and comparing end-times, which is added in a later iteration.
        """
        warnings: list[str] = []
        seen: dict[str, str] = {}   # time_of_day -> first task title that claimed it
        for task in schedule.tasks:
            if not task.time_of_day:
                continue
            if task.time_of_day in seen:
                warnings.append(
                    f"WARNING: conflict at {task.time_of_day} -- "
                    f"'{seen[task.time_of_day]}' and '{task.title}' are both scheduled then."
                )
            else:
                seen[task.time_of_day] = task.title
        return warnings

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def generate_schedule(self) -> Schedule:
        """Build and return a Schedule using a greedy priority-first algorithm.

        Steps:
        1. Call get_all_tasks() to retrieve the full task pool.
        2. Sort by PRIORITY_ORDER (high -> medium -> low).
        3. Fit tasks until available time is exhausted; remainder go to skipped_tasks.
        """
        schedule = Schedule()
        remaining = self.owner.get_available_time()
        sorted_tasks = sorted(self.get_all_tasks(), key=lambda t: PRIORITY_ORDER.get(t.priority, 99))
        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                schedule.add_task(task)
                remaining -= task.duration_minutes
            else:
                task.reason_skipped = "not enough time remaining"
                schedule.skipped_tasks.append(task)
        return schedule

    def explain_plan(self, schedule: Schedule) -> str:
        """Return a plain-English string explaining why each task was included or skipped."""
        lines = []
        for task in schedule.tasks:
            lines.append(f"[+] '{task.title}' included ({task.priority} priority, {task.duration_minutes} min).")
        for task in schedule.skipped_tasks:
            lines.append(f"[-] '{task.title}' skipped - {task.reason_skipped}.")
        return "\n".join(lines) if lines else "No tasks to schedule."
