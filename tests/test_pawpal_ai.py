"""
tests/test_pawpal_ai.py
Tests for the PawPal Care Coach retrieval and symptom-guidance layer.
"""

from pawpal_ai import create_default_care_advisor, load_knowledge_documents, load_symptom_examples
from pawpal_system import Owner, Pet, Scheduler


class TestPetCareAdvisor:
    """Tests for local classification, retrieval, and task suggestion flow."""

    def test_seed_data_loads(self):
        """The project should ship with a usable symptom dataset and KB."""
        examples = load_symptom_examples()
        documents = load_knowledge_documents()

        assert len(examples) >= 20
        assert len(documents) >= 5

    def test_digestive_symptoms_classify_and_retrieve(self):
        """Vomiting and diarrhea text should route to digestive guidance."""
        advisor = create_default_care_advisor()
        pet = Pet(name="Luna", species="cat", age=5)

        result = advisor.advise(pet, "My cat keeps vomiting and had diarrhea after breakfast.")

        assert result.condition == "Digestive Issues"
        assert result.confidence >= 0.45
        assert result.is_urgent is False
        assert any("aspca.org" in citation.source_url for citation in result.citations)

    def test_parasite_query_returns_parasite_category(self):
        """Worm and flea language should route to parasite guidance."""
        advisor = create_default_care_advisor()
        pet = Pet(name="Mochi", species="dog", age=3)

        result = advisor.advise(pet, "I found worms in my dog's stool and now he seems itchy.")

        assert result.condition == "Parasites"
        assert any("parasite" in citation.title.lower() for citation in result.citations)

    def test_urgent_case_triggers_escalation_and_callback_task(self):
        """Clear red-flag symptom text should trigger escalation and urgent follow-up."""
        advisor = create_default_care_advisor()
        pet = Pet(name="Mochi", species="dog", age=3)

        result = advisor.advise(
            pet,
            "My dog has sudden severe abdominal distension and keeps vomiting.",
        )

        assert result.escalation_message is not None
        assert result.is_urgent is True
        assert "Contact a veterinarian" in result.escalation_message
        assert result.suggested_tasks[0].title == "Call veterinary clinic"

    def test_suggested_tasks_can_be_added_to_scheduler(self):
        """Advice tasks should convert cleanly into normal PawPal schedule tasks."""
        advisor = create_default_care_advisor()
        pet = Pet(name="Luna", species="cat", age=5)
        owner = Owner(name="Jordan", available_minutes_per_day=60)
        owner.add_pet(pet)

        result = advisor.advise(pet, "My cat keeps scratching one ear and it smells bad.")
        for suggestion in result.suggested_tasks[:2]:
            pet.add_task(suggestion.to_task())

        schedule = Scheduler(owner).generate_schedule()
        scheduled_titles = [task.title for task in schedule.tasks]

        assert scheduled_titles
        assert any(title in scheduled_titles for title in ["Schedule ear exam with vet", "Check ears for odor or discharge"])

    def test_other_species_get_scope_note(self):
        """Non-dog and non-cat pets should get a scope warning."""
        advisor = create_default_care_advisor()
        pet = Pet(name="Pip", species="other", age=2)

        result = advisor.advise(pet, "My rabbit has a broken leg after an accident.")

        assert result.scope_note is not None
