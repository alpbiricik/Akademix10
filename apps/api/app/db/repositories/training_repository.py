from app.services import mock_store


class TrainingRepository:
    """Training content persistence boundary backed by mock_store for Phase 2G."""

    def list_templates(self):
        return mock_store.training_templates

    def get_template(self, template_id: str):
        return next((template for template in mock_store.training_templates if template.id == template_id), None)

    def list_modules(self):
        return mock_store.training_modules

    def get_module(self, module_id: str):
        return next((module for module in mock_store.training_modules if module.id == module_id), None)

    def get_states_for_module(self, module_id: str):
        return [state for state in mock_store.training_states if state.moduleId == module_id]

    def list_company_trainings(self, company_id: str = "company-demo"):
        return mock_store.get_company_templates(company_id)
