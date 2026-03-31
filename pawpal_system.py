"""
pawpal_system.py
Logic layer for PawPal+. Contains all backend classes.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """Represents the pet owner and their daily time constraints."""

    def __init__(self, name: str, available_minutes_per_day: int, preferences: list[str] | None = None):
        self.name = name
        self.available_minutes_per_day = available_minutes_per_day
        self.preferences: list[str] = preferences or []

    def get_available_time(self) -> int:
        """Return the number of minutes available for pet care today."""
        pass

    def update_preferences(self, prefs: list[str]) -> None:
        """Replace the owner's preference list with the given list."""
        pass


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

class Pet:
    """Represents the pet being cared for."""

    def __init__(self, name: str, species: str, age: int, special_needs: list[str] | None = None):
        self.name = name
        self.species = species          # e.g. "dog", "cat", "other"
        self.age = age                  # in years
        self.special_needs: list[str] = special_needs or []

    def get_info(self) -> str:
        """Return a human-readable summary of the pet's basic info."""
        pass


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

VALID_PRIORITIES = ("low", "medium", "high")
VALID_FREQUENCIES = ("daily", "weekly", "as-needed")


class Task:
    """Represents a single pet care activity."""

    def __init__(
        self,
        title: str,
        duration_minutes: int,
        priority: str,
        frequency: str = "daily",
        category: str = "general",
    ):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority        # "low", "medium", or "high"
        self.frequency = frequency      # "daily", "weekly", or "as-needed"
        self.category = category        # e.g. "exercise", "feeding", "medical"

    def is_valid(self) -> bool:
        """Return True if the task has a positive duration and a recognised priority."""
        pass

    def to_dict(self) -> dict:
        """Return a plain-dict representation of the task (useful for Streamlit tables)."""
        pass


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

class Schedule:
    """Represents a single day's ordered care plan produced by the Scheduler."""

    def __init__(self):
        self.tasks: list[Task] = []         # tasks that fit and will be done
        self.skipped_tasks: list[Task] = [] # tasks that were dropped due to constraints
        self.total_duration: int = 0        # sum of fitted task durations

    def add_task(self, task: Task) -> None:
        """Append a task to the scheduled list and update total_duration."""
        pass

    def get_total_duration(self) -> int:
        """Return the total minutes consumed by scheduled tasks."""
        pass

    def get_summary(self) -> str:
        """Return a formatted string listing scheduled and skipped tasks."""
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Scheduling engine — combines owner constraints, pet info, and tasks
    to produce a daily Schedule."""

    def __init__(self, owner: Owner, pet: Pet):
        self.owner = owner
        self.pet = pet
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the pool of tasks the scheduler can consider."""
        pass

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title from the pool (if it exists)."""
        pass

    def generate_schedule(self) -> Schedule:
        """Apply scheduling logic and return a Schedule for today.

        Strategy (greedy by priority):
        1. Sort tasks: high → medium → low priority.
        2. Iterate; fit each task if remaining time allows.
        3. Tasks that don't fit go into Schedule.skipped_tasks.
        """
        pass

    def explain_plan(self, schedule: Schedule) -> str:
        """Return a plain-English explanation of why each task was included or skipped."""
        pass
