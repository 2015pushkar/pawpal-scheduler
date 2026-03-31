"""
main.py
Temporary testing ground -- verifies PawPal+ logic works in the terminal.
Run with: python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Build the data  (tasks deliberately added out of chronological order)
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes_per_day=120)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks -- time_of_day added OUT OF ORDER to test sort_by_time
mochi.add_task(Task("Evening walk",   duration_minutes=30, priority="medium",
                    category="exercise",    time_of_day="18:00", frequency="daily"))
mochi.add_task(Task("Breakfast",      duration_minutes=10, priority="high",
                    category="feeding",     time_of_day="07:30", frequency="daily"))
mochi.add_task(Task("Training",       duration_minutes=20, priority="medium",
                    category="enrichment",  time_of_day="10:00", frequency="weekly"))
mochi.add_task(Task("Morning walk",   duration_minutes=30, priority="high",
                    category="exercise",    time_of_day="08:00", frequency="daily"))

# Luna's tasks -- "Feeding" intentionally shares 07:30 with Mochi's Breakfast
# to trigger conflict detection across pets
luna.add_task(Task("Feeding",         duration_minutes=10, priority="high",
                   category="feeding",      time_of_day="07:30", frequency="daily"))
luna.add_task(Task("Brushing",        duration_minutes=15, priority="medium",
                   category="grooming",     time_of_day="09:00", frequency="weekly"))
luna.add_task(Task("Laser toy play",  duration_minutes=20, priority="low",
                   category="enrichment",   time_of_day="",      frequency="as-needed"))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler(owner)

# ---------------------------------------------------------------------------
# Helper printing
# ---------------------------------------------------------------------------

W = 60

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
for t in sorted_tasks:
    time_label = t.time_of_day if t.time_of_day else "(no time)"
    row(f"  {time_label}  {t.title:<22}  {t.priority}")
print()

# ---------------------------------------------------------------------------
# 2. Filter by pet
# ---------------------------------------------------------------------------

section("FILTER BY PET  (Mochi only)")
mochi_tasks = scheduler.filter_by_pet(all_tasks, "Mochi")
for t in mochi_tasks:
    row(f"  {t.title:<30} {t.duration_minutes} min")
print()

# ---------------------------------------------------------------------------
# 3. Generate schedule + conflict detection
# ---------------------------------------------------------------------------

section("SCHEDULED TASKS  (greedy, priority-first)")
schedule = scheduler.generate_schedule()
for t in schedule.tasks:
    time_label = t.time_of_day if t.time_of_day else "     "
    row(f"  {time_label}  {t.title:<22}  {t.priority:<6}  {t.duration_minutes} min")
divider()
row(f"  Total: {schedule.get_total_duration()} / {owner.available_minutes_per_day} min")
print()

# Conflict detection
conflicts = scheduler.detect_conflicts(schedule)
section("CONFLICT DETECTION")
if conflicts:
    for w in conflicts:
        row("  " + w[:W - 4])
else:
    row("  No conflicts detected.")
print()

# ---------------------------------------------------------------------------
# 4. Recurring task completion
# ---------------------------------------------------------------------------

section("RECURRING TASK COMPLETION")
# Mark Mochi's "Breakfast" (daily) as complete via the Scheduler
breakfast = next(t for t in mochi.tasks if t.title == "Breakfast")
row(f"  Before: Mochi has {len(mochi.tasks)} task(s), Breakfast completed={breakfast.completed}")

next_task = scheduler.mark_task_complete(breakfast, mochi)

row(f"  After:  Mochi has {len(mochi.tasks)} task(s), Breakfast completed={breakfast.completed}")
if next_task:
    row(f"  New task created: '{next_task.title}' due {next_task.due_date}")
print()

# ---------------------------------------------------------------------------
# 5. Filter by status (show only incomplete tasks for Mochi after completion)
# ---------------------------------------------------------------------------

section("FILTER BY STATUS  (Mochi incomplete tasks)")
mochi_tasks_now = mochi.get_tasks()
incomplete = scheduler.filter_by_status(mochi_tasks_now, completed=False)
for t in incomplete:
    row(f"  [ ] {t.title:<28} due {t.due_date}")
print()

# ---------------------------------------------------------------------------
# 6. Explanation
# ---------------------------------------------------------------------------

section("EXPLANATION")
for line in scheduler.explain_plan(schedule).splitlines():
    row("  " + line[:W - 4])
divider("=")
print()
