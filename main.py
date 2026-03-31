"""
main.py
Temporary testing ground -- verifies PawPal+ logic works in the terminal.
Run with: python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Build the data
# ---------------------------------------------------------------------------

owner = Owner(name="Jordan", available_minutes_per_day=90)

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks
mochi.add_task(Task("Morning walk",   duration_minutes=30, priority="high",   category="exercise"))
mochi.add_task(Task("Breakfast",      duration_minutes=10, priority="high",   category="feeding"))
mochi.add_task(Task("Training",       duration_minutes=20, priority="medium", category="enrichment"))

# Luna's tasks
luna.add_task(Task("Feeding",         duration_minutes=10, priority="high",   category="feeding"))
luna.add_task(Task("Brushing",        duration_minutes=15, priority="medium", category="grooming"))
luna.add_task(Task("Laser toy play",  duration_minutes=20, priority="low",    category="enrichment"))

owner.add_pet(mochi)
owner.add_pet(luna)

# ---------------------------------------------------------------------------
# Generate schedule
# ---------------------------------------------------------------------------

scheduler = Scheduler(owner)
schedule  = scheduler.generate_schedule()
plan_text = scheduler.explain_plan(schedule)

# ---------------------------------------------------------------------------
# Pretty-print Today's Schedule (ASCII borders for Windows compatibility)
# ---------------------------------------------------------------------------

W = 54  # total inner width

def divider(char="-"):
    print("+" + char * W + "+")

def row(text=""):
    print("| " + text.ljust(W - 2) + " |")

def fmt_task(task: Task) -> str:
    checkbox = "[x]" if task.completed else "[ ]"
    badge    = f"[{task.priority.upper()}]"
    return f"{checkbox} {task.title:<24} {task.duration_minutes:>3} min  {badge}"

print()
divider("=")
row("TODAY'S PAWPAL+ SCHEDULE")
row(f"Owner: {owner.name}  |  Time budget: {owner.available_minutes_per_day} min")
divider("=")

if schedule.tasks:
    row("SCHEDULED TASKS")
    divider()
    for task in schedule.tasks:
        row(fmt_task(task))
    divider()
    total = schedule.get_total_duration()
    row(f"Total: {total} min used / {owner.available_minutes_per_day} min available")
else:
    row("No tasks fit within the available time.")

if schedule.skipped_tasks:
    divider("=")
    row("SKIPPED (not enough time remaining)")
    divider()
    for task in schedule.skipped_tasks:
        reason = f" <- {task.reason_skipped}" if task.reason_skipped else ""
        row(f"[-] {task.title:<24} {task.duration_minutes:>3} min{reason}")

divider("=")
row("EXPLANATION")
divider()
for line in plan_text.splitlines():
    row(line[:W - 2])
divider("=")
print()
