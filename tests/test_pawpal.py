"""
tests/test_pawpal.py
Unit tests for PawPal+ core logic.
Run with: pytest tests/
"""

import pytest
from pawpal_system import Task, Pet


class TestTaskCompletion:
    """Tests for Task.mark_complete()."""

    def test_mark_complete_changes_status(self):
        """Calling mark_complete() should set task.completed to True."""
        task = Task(title="Morning walk", duration_minutes=30, priority="high")
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_is_idempotent(self):
        """Calling mark_complete() twice should not raise and status stays True."""
        task = Task(title="Feeding", duration_minutes=10, priority="high")
        task.mark_complete()
        task.mark_complete()
        assert task.completed is True


class TestTaskAddition:
    """Tests for Pet.add_task()."""

    def test_add_task_increases_count(self):
        """Adding a task to a Pet should increase its task list length by 1."""
        pet = Pet(name="Mochi", species="dog", age=3)
        assert len(pet.tasks) == 0
        pet.add_task(Task("Walk", duration_minutes=20, priority="medium"))
        assert len(pet.tasks) == 1

    def test_add_multiple_tasks(self):
        """Adding three tasks should result in a task list of length 3."""
        pet = Pet(name="Luna", species="cat", age=5)
        pet.add_task(Task("Feeding",  duration_minutes=10, priority="high"))
        pet.add_task(Task("Brushing", duration_minutes=15, priority="medium"))
        pet.add_task(Task("Play",     duration_minutes=20, priority="low"))
        assert len(pet.tasks) == 3

    def test_add_invalid_task_raises(self):
        """Adding a task with zero duration should raise ValueError."""
        pet = Pet(name="Mochi", species="dog", age=3)
        bad_task = Task(title="Ghost task", duration_minutes=0, priority="high")
        with pytest.raises(ValueError):
            pet.add_task(bad_task)
