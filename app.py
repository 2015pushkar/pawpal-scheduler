import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state vault
#
# st.session_state works like a dictionary that survives reruns.
# Pattern: check before creating so we never overwrite existing data.
#   if "owner" not in st.session_state:
#       st.session_state.owner = Owner(...)
# ---------------------------------------------------------------------------

# ── Step 1: Owner setup ─────────────────────────────────────────────────────
st.header("1. Owner Profile")

with st.form("owner_form"):
    owner_name      = st.text_input("Your name", value="Jordan")
    available_mins  = st.number_input("Minutes available for pet care today",
                                      min_value=10, max_value=480, value=90, step=5)
    save_owner      = st.form_submit_button("Save profile")

if save_owner:
    # Always update when the form is submitted so the owner can edit their profile.
    st.session_state.owner = Owner(name=owner_name,
                                   available_minutes_per_day=int(available_mins))
    st.success(f"Profile saved for {owner_name} ({available_mins} min/day).")

if "owner" not in st.session_state:
    st.info("Fill in your profile above to get started.")
    st.stop()          # Nothing below can work without an Owner.

owner: Owner = st.session_state.owner

# ── Step 2: Add a pet ───────────────────────────────────────────────────────
st.divider()
st.header("2. Your Pets")

with st.form("pet_form"):
    pet_name    = st.text_input("Pet name", value="Mochi")
    pet_species = st.selectbox("Species", ["dog", "cat", "other"])
    pet_age     = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    add_pet_btn = st.form_submit_button("Add pet")

if add_pet_btn:
    # Guard: don't add a duplicate name
    existing_names = [p.name for p in owner.pets]
    if pet_name in existing_names:
        st.warning(f"A pet named '{pet_name}' already exists.")
    else:
        new_pet = Pet(name=pet_name, species=pet_species, age=int(pet_age))
        owner.add_pet(new_pet)          # <-- real method call, stored inside owner in session_state
        st.success(f"Added {new_pet.get_info()} to {owner.name}'s pets!")

if not owner.pets:
    st.info("No pets yet. Add one above.")
else:
    st.subheader(f"{owner.name}'s pets")
    for pet in owner.pets:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{pet.get_info()}** — {len(pet.tasks)} task(s)")
        with col2:
            if st.button("Remove", key=f"remove_pet_{pet.name}"):
                owner.remove_pet(pet.name)
                st.rerun()

# ── Step 3: Add tasks ───────────────────────────────────────────────────────
st.divider()
st.header("3. Care Tasks")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        selected_pet  = st.selectbox("Assign task to", pet_names)
        task_title    = st.text_input("Task", value="Morning walk")
        task_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        task_priority = st.selectbox("Priority", ["high", "medium", "low"])
        task_category = st.text_input("Category (optional)", value="exercise")
        add_task_btn  = st.form_submit_button("Add task")

    if add_task_btn:
        target_pet = next(p for p in owner.pets if p.name == selected_pet)
        new_task   = Task(title=task_title,
                          duration_minutes=int(task_duration),
                          priority=task_priority,
                          category=task_category or "general")
        try:
            target_pet.add_task(new_task)   # <-- real method call; validates & appends
            st.success(f"Added '{task_title}' to {selected_pet}.")
        except ValueError as e:
            st.error(str(e))

    # Show all current tasks grouped by pet
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.subheader("Current tasks")
        for pet in owner.pets:
            if pet.tasks:
                st.markdown(f"**{pet.get_info()}**")
                for task in pet.get_tasks():
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.write(task.title)
                    c2.write(f"{task.duration_minutes} min")
                    c3.write(task.priority)
                    if c4.button("Remove", key=f"remove_task_{pet.name}_{task.title}"):
                        pet.remove_task(task.title)
                        st.rerun()

# ── Step 4: Generate schedule ───────────────────────────────────────────────
st.divider()
st.header("4. Today's Schedule")

if not owner.get_all_tasks():
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner)
        schedule  = scheduler.generate_schedule()

        st.subheader(f"Plan for {owner.name} — {schedule.get_total_duration()} / {owner.available_minutes_per_day} min used")

        if schedule.tasks:
            st.markdown("**Scheduled**")
            for task in schedule.tasks:
                st.markdown(f"- [ ] **{task.title}** &nbsp; `{task.duration_minutes} min` &nbsp; `{task.priority}`")

        if schedule.skipped_tasks:
            st.markdown("**Skipped** (not enough time)")
            for task in schedule.skipped_tasks:
                st.markdown(f"- ~~{task.title}~~ — {task.reason_skipped}")

        with st.expander("Why this plan?"):
            st.text(scheduler.explain_plan(schedule))
