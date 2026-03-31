import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner — smart scheduling, conflict detection, and recurring tasks.")

# ---------------------------------------------------------------------------
# Session state vault
#
# st.session_state is a dictionary that survives Streamlit reruns.
# Pattern:  if "key" not in st.session_state: initialise it once.
# After that, read/write st.session_state.key freely.
# ---------------------------------------------------------------------------

PRIORITY_COLORS = {"high": "🔴", "medium": "🟡", "low": "🟢"}
FREQ_LABELS     = {"daily": "📅 Daily", "weekly": "🗓 Weekly", "as-needed": "🔔 As needed"}

# ── Section 1: Owner profile ────────────────────────────────────────────────
st.header("1. Owner Profile")

with st.form("owner_form"):
    col1, col2 = st.columns([2, 1])
    owner_name     = col1.text_input("Your name", value="Jordan")
    available_mins = col2.number_input("Minutes available today",
                                       min_value=10, max_value=480, value=90, step=5)
    save_owner = st.form_submit_button("Save profile", use_container_width=True)

if save_owner:
    st.session_state.owner = Owner(name=owner_name,
                                   available_minutes_per_day=int(available_mins))
    st.success(f"Profile saved — {owner_name} has {available_mins} min today.")

if "owner" not in st.session_state:
    st.info("Fill in your profile above to get started.")
    st.stop()

owner: Owner     = st.session_state.owner
scheduler        = Scheduler(owner)     # created once per rerun; cheap to construct

# ── Section 2: Pets ─────────────────────────────────────────────────────────
st.divider()
st.header("2. Your Pets")

with st.form("pet_form"):
    col1, col2, col3 = st.columns([2, 2, 1])
    pet_name    = col1.text_input("Pet name", value="Mochi")
    pet_species = col2.selectbox("Species", ["dog", "cat", "other"])
    pet_age     = col3.number_input("Age", min_value=0, max_value=30, value=3)
    add_pet_btn = st.form_submit_button("Add pet", use_container_width=True)

if add_pet_btn:
    if pet_name in [p.name for p in owner.pets]:
        st.warning(f"A pet named **{pet_name}** already exists.")
    else:
        owner.add_pet(Pet(name=pet_name, species=pet_species, age=int(pet_age)))
        st.success(f"Added **{pet_name}** ({pet_species}) to your family!")

if not owner.pets:
    st.info("No pets yet — add one above.")
else:
    for pet in owner.pets:
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"**{pet.get_info()}** &nbsp; `{len(pet.tasks)} task(s)`")
        if col2.button("Remove", key=f"remove_pet_{pet.name}"):
            owner.remove_pet(pet.name)
            st.rerun()

# ── Section 3: Care tasks ───────────────────────────────────────────────────
st.divider()
st.header("3. Care Tasks")

if not owner.pets:
    st.info("Add a pet first.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        col1, col2 = st.columns(2)
        selected_pet  = col1.selectbox("Assign to", pet_names)
        task_title    = col2.text_input("Task name", value="Morning walk")

        col3, col4, col5 = st.columns(3)
        task_duration = col3.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        task_priority = col4.selectbox("Priority", ["high", "medium", "low"])
        task_freq     = col5.selectbox("Frequency", ["daily", "weekly", "as-needed"])

        col6, col7 = st.columns(2)
        task_category = col6.text_input("Category", value="exercise")
        task_time     = col7.text_input("Time (HH:MM, optional)", value="",
                                        placeholder="e.g. 08:00")
        add_task_btn = st.form_submit_button("Add task", use_container_width=True)

    if add_task_btn:
        target_pet = next(p for p in owner.pets if p.name == selected_pet)
        new_task   = Task(title=task_title,
                          duration_minutes=int(task_duration),
                          priority=task_priority,
                          frequency=task_freq,
                          category=task_category or "general",
                          time_of_day=task_time.strip())
        try:
            target_pet.add_task(new_task)
            st.success(f"Added **{task_title}** to {selected_pet}.")
        except ValueError as e:
            st.error(str(e))

    # Current tasks display — sorted chronologically using Scheduler.sort_by_time()
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.subheader("Current tasks (sorted by time)")
        sorted_all = scheduler.sort_by_time(all_tasks)

        rows = []
        for task in sorted_all:
            rows.append({
                "Time":     task.time_of_day or "—",
                "Task":     task.title,
                "Pet":      next((p.name for p in owner.pets if task in p.tasks), "?"),
                "Duration": f"{task.duration_minutes} min",
                "Priority": f"{PRIORITY_COLORS.get(task.priority, '')} {task.priority}",
                "Repeat":   FREQ_LABELS.get(task.frequency, task.frequency),
                "Done":     "✔" if task.completed else "",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Per-pet remove controls
        with st.expander("Remove a task"):
            for pet in owner.pets:
                if pet.tasks:
                    st.markdown(f"**{pet.name}**")
                    for task in pet.get_tasks():
                        col1, col2 = st.columns([5, 1])
                        col1.write(f"{task.title}  `{task.duration_minutes} min`")
                        if col2.button("Remove", key=f"rm_{pet.name}_{task.title}"):
                            pet.remove_task(task.title)
                            st.rerun()

# ── Section 4: Today's schedule ─────────────────────────────────────────────
st.divider()
st.header("4. Today's Schedule")

if not owner.get_all_tasks():
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule", type="primary", use_container_width=True):
        schedule = scheduler.generate_schedule()

        # ── Time budget progress bar ────────────────────────────────────────
        used  = schedule.get_total_duration()
        total = owner.available_minutes_per_day
        pct   = min(used / total, 1.0)
        st.progress(pct, text=f"{used} / {total} min used")

        # ── Conflict warnings (shown prominently before the task list) ──────
        conflicts = scheduler.detect_conflicts(schedule)
        if conflicts:
            st.markdown("#### ⚠️ Scheduling Conflicts Detected")
            for warning in conflicts:
                # Extract just the time from the warning for a helpful callout
                st.warning(
                    f"**Time conflict:** {warning}\n\n"
                    "_Two tasks are assigned the same start time. "
                    "Consider adjusting one of them._",
                    icon="⚠️"
                )

        # ── Scheduled tasks (sorted by time_of_day) ─────────────────────────
        if schedule.tasks:
            st.markdown("#### Scheduled tasks")
            time_sorted = scheduler.sort_by_time(schedule.tasks)
            sched_rows  = []
            for task in time_sorted:
                sched_rows.append({
                    "Time":     task.time_of_day or "—",
                    "Task":     task.title,
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": f"{PRIORITY_COLORS.get(task.priority, '')} {task.priority}",
                    "Repeat":   FREQ_LABELS.get(task.frequency, task.frequency),
                })
            st.dataframe(sched_rows, use_container_width=True, hide_index=True)

        # ── Skipped tasks ────────────────────────────────────────────────────
        if schedule.skipped_tasks:
            st.markdown("#### Skipped (not enough time)")
            for task in schedule.skipped_tasks:
                st.error(
                    f"**{task.title}** ({task.duration_minutes} min) — {task.reason_skipped}",
                    icon="🚫"
                )

        # ── Mark tasks complete ──────────────────────────────────────────────
        if schedule.tasks:
            st.markdown("#### Mark tasks complete")
            st.caption("Completing a daily or weekly task will queue its next occurrence automatically.")
            for task in schedule.tasks:
                if not task.completed:
                    owner_pet = next((p for p in owner.pets if task in p.tasks), None)
                    label = f"{task.title}  `{task.duration_minutes} min` `{task.priority}`"
                    if st.button(f"Done: {task.title}", key=f"done_{task.title}"):
                        if owner_pet:
                            next_task = scheduler.mark_task_complete(task, owner_pet)
                            if next_task:
                                st.success(
                                    f"**{task.title}** marked complete. "
                                    f"Next occurrence queued for **{next_task.due_date}**.",
                                    icon="✅"
                                )
                            else:
                                st.success(f"**{task.title}** marked complete.", icon="✅")
                            st.rerun()

        # ── Explanation expander ────────────────────────────────────────────
        with st.expander("Why this plan?"):
            st.text(scheduler.explain_plan(schedule))
