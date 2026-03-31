"""
tests/test_pawpal.py
Unit tests for PawPal+ core logic.
Run with: pytest tests/
"""

import pytest
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Schedule, Scheduler


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_task(title="Walk", duration=20, priority="medium",
              frequency="daily", time_of_day="", category="general"):
    """Return a Task with sensible defaults so tests stay concise."""
    return Task(title=title, duration_minutes=duration, priority=priority,
                frequency=frequency, category=category, time_of_day=time_of_day)


def make_scheduler(*pets, minutes=120):
    """Return a Scheduler wired to an Owner who owns the given pets."""
    owner = Owner(name="Jordan", available_minutes_per_day=minutes)
    for pet in pets:
        owner.add_pet(pet)
    return Scheduler(owner)


# ---------------------------------------------------------------------------
# 1. Task completion
# ---------------------------------------------------------------------------

class TestTaskCompletion:
    """Tests for Task.mark_complete()."""

    def test_mark_complete_changes_status(self):
        """Calling mark_complete() should set task.completed to True."""
        task = make_task("Morning walk", duration=30, priority="high")
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_is_idempotent(self):
        """Calling mark_complete() twice should not raise and status stays True."""
        task = make_task("Feeding", duration=10, priority="high")
        task.mark_complete()
        task.mark_complete()
        assert task.completed is True


# ---------------------------------------------------------------------------
# 2. Task addition / validation
# ---------------------------------------------------------------------------

class TestTaskAddition:
    """Tests for Pet.add_task()."""

    def test_add_task_increases_count(self):
        """Adding a task to a Pet should increase its task list length by 1."""
        pet = Pet(name="Mochi", species="dog", age=3)
        assert len(pet.tasks) == 0
        pet.add_task(make_task())
        assert len(pet.tasks) == 1

    def test_add_multiple_tasks(self):
        """Adding three tasks should result in a task list of length 3."""
        pet = Pet(name="Luna", species="cat", age=5)
        pet.add_task(make_task("Feeding",  duration=10, priority="high"))
        pet.add_task(make_task("Brushing", duration=15, priority="medium"))
        pet.add_task(make_task("Play",     duration=20, priority="low"))
        assert len(pet.tasks) == 3

    def test_add_invalid_task_raises(self):
        """Adding a task with zero duration should raise ValueError."""
        pet = Pet(name="Mochi", species="dog", age=3)
        with pytest.raises(ValueError):
            pet.add_task(make_task("Ghost", duration=0, priority="high"))

    def test_add_invalid_priority_raises(self):
        """Adding a task with an unrecognised priority should raise ValueError."""
        pet = Pet(name="Mochi", species="dog", age=3)
        with pytest.raises(ValueError):
            pet.add_task(make_task("Walk", duration=20, priority="urgent"))


# ---------------------------------------------------------------------------
# 3. Sorting correctness
# ---------------------------------------------------------------------------

class TestSortByTime:
    """Tests for Scheduler.sort_by_time()."""

    def test_tasks_returned_in_chronological_order(self):
        """Tasks with time_of_day should come back sorted earliest-first."""
        pet = Pet(name="Mochi", species="dog", age=3)
        pet.add_task(make_task("Evening walk",  duration=30, time_of_day="18:00"))
        pet.add_task(make_task("Afternoon nap", duration=20, time_of_day="13:00"))
        pet.add_task(make_task("Breakfast",     duration=10, time_of_day="07:30"))
        scheduler = make_scheduler(pet)

        sorted_tasks = scheduler.sort_by_time(pet.get_tasks())
        times = [t.time_of_day for t in sorted_tasks]
        assert times == ["07:30", "13:00", "18:00"]

    def test_untimed_tasks_sort_to_end(self):
        """Tasks without time_of_day should appear after all timed tasks."""
        pet = Pet(name="Luna", species="cat", age=5)
        pet.add_task(make_task("Play",    duration=20, time_of_day=""))
        pet.add_task(make_task("Feeding", duration=10, time_of_day="08:00"))
        scheduler = make_scheduler(pet)

        sorted_tasks = scheduler.sort_by_time(pet.get_tasks())
        assert sorted_tasks[0].title == "Feeding"
        assert sorted_tasks[-1].title == "Play"

    def test_sort_empty_list_returns_empty(self):
        """sort_by_time on an empty list should return [] without raising."""
        scheduler = make_scheduler()
        assert scheduler.sort_by_time([]) == []

    def test_all_untimed_tasks_preserves_length(self):
        """Sorting tasks that all have no time_of_day should return all of them."""
        pet = Pet(name="Rex", species="dog", age=2)
        pet.add_task(make_task("A", duration=10))
        pet.add_task(make_task("B", duration=10))
        scheduler = make_scheduler(pet)
        result = scheduler.sort_by_time(pet.get_tasks())
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 4. Recurrence logic
# ---------------------------------------------------------------------------

class TestRecurrence:
    """Tests for Scheduler.mark_task_complete() recurrence behaviour."""

    def test_daily_task_creates_next_occurrence(self):
        """Completing a daily task should add a new task to the pet's list."""
        pet = Pet(name="Mochi", species="dog", age=3)
        task = make_task("Breakfast", duration=10, priority="high", frequency="daily")
        pet.add_task(task)
        scheduler = make_scheduler(pet)

        assert len(pet.tasks) == 1
        scheduler.mark_task_complete(task, pet)
        assert len(pet.tasks) == 2

    def test_daily_task_due_date_is_tomorrow(self):
        """The follow-up task for a daily task should be due tomorrow."""
        pet = Pet(name="Mochi", species="dog", age=3)
        task = make_task("Breakfast", duration=10, priority="high", frequency="daily")
        pet.add_task(task)
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(task, pet)
        assert next_task is not None
        assert next_task.due_date == date.today() + timedelta(days=1)

    def test_weekly_task_due_date_is_seven_days(self):
        """The follow-up task for a weekly task should be due in 7 days."""
        pet = Pet(name="Luna", species="cat", age=5)
        task = make_task("Vet visit", duration=60, priority="high", frequency="weekly")
        pet.add_task(task)
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(task, pet)
        assert next_task is not None
        assert next_task.due_date == date.today() + timedelta(days=7)

    def test_as_needed_task_creates_no_followup(self):
        """Completing an as-needed task should NOT add a new task."""
        pet = Pet(name="Rex", species="dog", age=2)
        task = make_task("Bath", duration=30, priority="medium", frequency="as-needed")
        pet.add_task(task)
        scheduler = make_scheduler(pet)

        result = scheduler.mark_task_complete(task, pet)
        assert result is None
        assert len(pet.tasks) == 1         # no new task added

    def test_completed_flag_set_after_mark_complete(self):
        """mark_task_complete should still flip task.completed to True."""
        pet = Pet(name="Mochi", species="dog", age=3)
        task = make_task("Walk", duration=20, priority="high", frequency="daily")
        pet.add_task(task)
        scheduler = make_scheduler(pet)

        scheduler.mark_task_complete(task, pet)
        assert task.completed is True


# ---------------------------------------------------------------------------
# 5. Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Tests for Scheduler.detect_conflicts()."""

    def test_duplicate_time_raises_warning(self):
        """Two tasks at the same time_of_day should produce exactly one warning."""
        pet = Pet(name="Mochi", species="dog", age=3)
        pet.add_task(make_task("Breakfast",   duration=10, priority="high",   time_of_day="07:30"))
        pet.add_task(make_task("Morning meds",duration=5,  priority="high",   time_of_day="07:30"))
        scheduler = make_scheduler(pet)
        schedule = scheduler.generate_schedule()

        warnings = scheduler.detect_conflicts(schedule)
        assert len(warnings) == 1
        assert "07:30" in warnings[0]

    def test_different_times_no_conflict(self):
        """Tasks at distinct times should produce no warnings."""
        pet = Pet(name="Luna", species="cat", age=5)
        pet.add_task(make_task("Feeding",  duration=10, priority="high",   time_of_day="08:00"))
        pet.add_task(make_task("Brushing", duration=15, priority="medium", time_of_day="09:00"))
        scheduler = make_scheduler(pet)
        schedule = scheduler.generate_schedule()

        assert scheduler.detect_conflicts(schedule) == []

    def test_conflict_across_different_pets(self):
        """Two tasks from different pets assigned the same slot should still conflict."""
        mochi = Pet(name="Mochi", species="dog", age=3)
        luna  = Pet(name="Luna",  species="cat", age=5)
        mochi.add_task(make_task("Breakfast", duration=10, priority="high", time_of_day="07:30"))
        luna.add_task(make_task("Feeding",    duration=10, priority="high", time_of_day="07:30"))
        scheduler = make_scheduler(mochi, luna)
        schedule = scheduler.generate_schedule()

        warnings = scheduler.detect_conflicts(schedule)
        assert len(warnings) == 1

    def test_untimed_tasks_never_conflict(self):
        """Tasks with no time_of_day should never be flagged, even if there are many."""
        pet = Pet(name="Rex", species="dog", age=2)
        pet.add_task(make_task("Task A", duration=10, time_of_day=""))
        pet.add_task(make_task("Task B", duration=10, time_of_day=""))
        scheduler = make_scheduler(pet)
        schedule = scheduler.generate_schedule()

        assert scheduler.detect_conflicts(schedule) == []

    def test_no_conflict_on_empty_schedule(self):
        """detect_conflicts on a schedule with no tasks should return []."""
        scheduler = make_scheduler()
        assert scheduler.detect_conflicts(Schedule()) == []


# ---------------------------------------------------------------------------
# 6. Schedule generation edge cases
# ---------------------------------------------------------------------------

class TestScheduleGeneration:
    """Tests for Scheduler.generate_schedule() boundary conditions."""

    def test_schedule_never_exceeds_available_time(self):
        """Total scheduled duration must not exceed owner's available minutes."""
        pet = Pet(name="Mochi", species="dog", age=3)
        for i in range(6):
            pet.add_task(make_task(f"Task {i}", duration=30, priority="high"))
        scheduler = make_scheduler(pet, minutes=60)
        schedule = scheduler.generate_schedule()

        assert schedule.get_total_duration() <= 60

    def test_pet_with_no_tasks_produces_empty_schedule(self):
        """An owner whose pets have no tasks should get an empty schedule."""
        pet = Pet(name="Ghost", species="cat", age=1)
        scheduler = make_scheduler(pet)
        schedule = scheduler.generate_schedule()

        assert schedule.tasks == []
        assert schedule.skipped_tasks == []

    def test_owner_with_no_pets_produces_empty_schedule(self):
        """An owner with no pets at all should get an empty schedule without crashing."""
        scheduler = make_scheduler()
        schedule = scheduler.generate_schedule()

        assert schedule.tasks == []

    def test_high_priority_tasks_scheduled_before_low(self):
        """A high-priority task should appear in the schedule when a low one is skipped."""
        pet = Pet(name="Mochi", species="dog", age=3)
        pet.add_task(make_task("Low task",  duration=50, priority="low"))
        pet.add_task(make_task("High task", duration=50, priority="high"))
        scheduler = make_scheduler(pet, minutes=60)
        schedule = scheduler.generate_schedule()

        scheduled_titles = [t.title for t in schedule.tasks]
        assert "High task" in scheduled_titles
        assert "Low task" not in scheduled_titles
