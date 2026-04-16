# PawPal Care Coach

**PawPal Care Coach** is a grounded pet-care assistant that connects two workflows owners actually have:

- planning recurring daily care across multiple pets
- responding safely when a pet shows symptoms or a new care concern

Instead of letting a generative model make the whole decision, this project keeps the final action plan deterministic. The AI layer interprets symptom text, retrieves relevant local care guidance, and suggests follow-up tasks. The scheduler decides what fits into the day.

## Problem

Pet owners do not just need reminders. They need a way to turn messy real-world questions like `My cat vomited twice today and is hiding` into practical next steps without losing track of routine feeding, exercise, medication, and follow-up work.

Many tools separate those experiences:

- reminder apps manage routine tasks
- AI chat tools discuss symptoms

The gap is execution. Guidance is useful only if it becomes a concrete plan.

## Concept

PawPal+ combines a grounded care helper with a deterministic scheduler.

The care helper:

- classifies a symptom description into a small set of known categories
- retrieves relevant local care guidance with citations
- surfaces warning signs and escalation language
- suggests follow-up actions such as `Call veterinary clinic` or `Schedule ear exam with vet`

The scheduler then treats those follow-up actions as normal tasks and merges them with the owner's existing pet-care workload.

## Approach

- **Classification:** nearest-neighbor text similarity over a local symptom dataset in [data/pet_health_symptoms_dataset.csv](data/pet_health_symptoms_dataset.csv)
- **Retrieval:** local knowledge-base lookup from [knowledge_base/pet_care_docs.json](knowledge_base/pet_care_docs.json)
- **Response generation:** template-based summaries, care steps, warnings, citations, and task suggestions
- **Scheduling:** deterministic greedy prioritization over one shared `Task` model
- **Guardrails:** non-diagnosis framing, urgent escalation, source display, and limited-species scope warnings

## Architecture At A Glance

```text
manual pet tasks ------------------------------+
                                               |
symptom text -> classify -> retrieve guidance -> grounded advice -> suggested tasks -> Task
                                               |                                        |
                                               +----------------------------------------+
                                                                                        |
owner + pets + tasks -------------------------------------------------> Scheduler -> daily plan
```

For the detailed architecture diagrams and design framing, see [ARCHITECTURE.md](ARCHITECTURE.md).

## What It Does

- Creates a daily care schedule across multiple pets with priorities, recurring tasks, skipped-task reporting, and explanations
- Accepts free-text symptom or care questions
- Maps symptom text into one of five supported categories:
  - `Digestive Issues`
  - `Ear Infections`
  - `Skin Irritations`
  - `Parasites`
  - `Mobility Problems`
- Retrieves local guidance with source links, warning signs, and safe next steps
- Converts grounded guidance into follow-up tasks that can be added directly into the scheduler

## Why This Design Is Credible

- The AI layer is bounded to interpretation and guidance, not final decision-making
- All care guidance is grounded in local documents with explicit source URLs
- Manual tasks and AI-suggested tasks use the same domain model, so the workflow is coherent
- The scheduler is simple, transparent, and easy to test
- The repo includes both automated tests and a small evaluation harness

## Main Modules

- [pawpal_system.py](pawpal_system.py) - core task, pet, owner, schedule, and scheduler logic
- [pawpal_ai.py](pawpal_ai.py) - symptom classification, retrieval, guardrails, and suggested-task generation
- [app.py](app.py) - Streamlit UI
- [main.py](main.py) - terminal demo
- [evaluate_care_helper.py](evaluate_care_helper.py) - fixed-case evaluation harness

## Setup

```bash
# 1. Create and activate a virtual environment
py -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the Streamlit app
streamlit run app.py

# 4. Run the terminal demo
python main.py

# 5. Run the evaluation harness
python evaluate_care_helper.py

# 6. Run the tests
pytest tests -v
```

## Example Interactions

Example 1:

- Input: `My cat keeps vomiting and had diarrhea after breakfast.`
- Category: `Digestive Issues`
- Output: hydration monitoring steps, warning signs, source links, and suggested tasks like `Monitor food and water intake`

Example 2:

- Input: `My dog's ear smells bad and he keeps scratching it.`
- Category: `Ear Infections`
- Output: ear-check guidance, vet follow-up advice, warning signs, and a suggested task like `Schedule ear exam with vet`

Example 3:

- Input: `My dog has sudden severe abdominal distension and keeps vomiting.`
- Category: `Digestive Issues`
- Output: urgent escalation message, source-backed advice, and a high-priority task such as `Call veterinary clinic`

## Testing

The project has **30 automated tests** across the scheduler logic and the care-helper layer.

Covered scenarios include:

- schedule generation, recurrence, and conflict detection
- symptom classification across digestive, parasite, ear, and mobility language
- knowledge-base retrieval with source links
- urgent-case escalation
- converting suggested care tasks into normal PawPal schedule tasks
- scope warnings for unsupported species

Run all tests with:

```bash
.venv\Scripts\python -m pytest tests -q
```

## Project Structure

```text
app.py
ARCHITECTURE.md
data/
  pet_health_symptoms_dataset.csv
evaluate_care_helper.py
knowledge_base/
  pet_care_docs.json
main.py
pawpal_ai.py
pawpal_system.py
requirements.txt
tests/
  test_pawpal.py
  test_pawpal_ai.py
```
