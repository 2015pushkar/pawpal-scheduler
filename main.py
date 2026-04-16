"""
main.py
Terminal demo for PawPal+ and the new PawPal Care Coach helper.
Run with: python main.py
"""

from pawpal_ai import create_default_care_advisor
from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Build the data
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes_per_day=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna = Pet(name="Luna", species="cat", age=5)

mochi.add_task(Task("Evening walk", duration_minutes=30, priority="medium",
                    category="exercise", time_of_day="18:00", frequency="daily"))
mochi.add_task(Task("Breakfast", duration_minutes=10, priority="high",
                    category="feeding", time_of_day="07:30", frequency="daily"))
mochi.add_task(Task("Training", duration_minutes=20, priority="medium",
                    category="enrichment", time_of_day="10:00", frequency="weekly"))
mochi.add_task(Task("Morning walk", duration_minutes=30, priority="high",
                    category="exercise", time_of_day="08:00", frequency="daily"))

luna.add_task(Task("Feeding", duration_minutes=10, priority="high",
                   category="feeding", time_of_day="07:30", frequency="daily"))
luna.add_task(Task("Brushing", duration_minutes=15, priority="medium",
                   category="grooming", time_of_day="09:00", frequency="weekly"))
luna.add_task(Task("Laser toy play", duration_minutes=20, priority="low",
                   category="enrichment", time_of_day="", frequency="as-needed"))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler(owner)
care_advisor = create_default_care_advisor()


# ---------------------------------------------------------------------------
# Helper printing
# ---------------------------------------------------------------------------

W = 68


def divider(char="-"):
    print("+" + char * W + "+")


def row(text=""):
    print("| " + text.ljust(W - 2) + " |")


def section(title):
    divider("=")
    row(title)
    divider("=")


# ---------------------------------------------------------------------------
# 1. Sort by time
# ---------------------------------------------------------------------------

section("SORT BY TIME  (all tasks, chronological)")
all_tasks = scheduler.get_all_tasks()
sorted_tasks = scheduler.sort_by_time(all_tasks)
for task in sorted_tasks:
    time_label = task.time_of_day if task.time_of_day else "(no time)"
    row(f"  {time_label}  {task.title:<24}  {task.priority}")
print()


# ---------------------------------------------------------------------------
# 2. Filter by pet
# ---------------------------------------------------------------------------

section("FILTER BY PET  (Mochi only)")
mochi_tasks = scheduler.filter_by_pet(all_tasks, "Mochi")
for task in mochi_tasks:
    row(f"  {task.title:<34} {task.duration_minutes} min")
print()


# ---------------------------------------------------------------------------
# 3. Generate schedule + conflict detection
# ---------------------------------------------------------------------------

section("SCHEDULED TASKS  (greedy, priority-first)")
schedule = scheduler.generate_schedule()
for task in schedule.tasks:
    time_label = task.time_of_day if task.time_of_day else "     "
    row(f"  {time_label}  {task.title:<24}  {task.priority:<6}  {task.duration_minutes} min")
divider()
row(f"  Total: {schedule.get_total_duration()} / {owner.available_minutes_per_day} min")
print()

section("CONFLICT DETECTION")
conflicts = scheduler.detect_conflicts(schedule)
if conflicts:
    for warning in conflicts:
        row("  " + warning[:W - 4])
else:
    row("  No conflicts detected.")
print()


# ---------------------------------------------------------------------------
# 4. Recurring task completion
# ---------------------------------------------------------------------------

section("RECURRING TASK COMPLETION")
breakfast = next(task for task in mochi.tasks if task.title == "Breakfast")
row(f"  Before: Mochi has {len(mochi.tasks)} task(s), Breakfast completed={breakfast.completed}")

next_task = scheduler.mark_task_complete(breakfast, mochi)

row(f"  After:  Mochi has {len(mochi.tasks)} task(s), Breakfast completed={breakfast.completed}")
if next_task:
    row(f"  New task created: '{next_task.title}' due {next_task.due_date}")
print()


# ---------------------------------------------------------------------------
# 5. Pet-care helper demo
# ---------------------------------------------------------------------------

section("PET-CARE HELPER  (symptom classification + retrieval)")
query = "My cat vomited three times today and is hiding under the bed."
advice = care_advisor.advise(luna, query)
row("  Query:")
row("  " + query[:W - 4])
divider()
row(f"  Category: {advice.condition}  confidence={advice.confidence:.2f}")
row("  Summary:")
for line in advice.simple_summary.split(". "):
    if line.strip():
        row("  " + line.strip()[:W - 4])
divider()
row("  Suggested tasks:")
for suggestion in advice.suggested_tasks:
    row(f"  - {suggestion.title} ({suggestion.duration_minutes} min)")
print()


# ---------------------------------------------------------------------------
# 6. Explanation
# ---------------------------------------------------------------------------

section("EXPLANATION")
for line in scheduler.explain_plan(schedule).splitlines():
    row("  " + line[:W - 4])
divider("=")
print()
