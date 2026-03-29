from pydantic import BaseModel


class ModuleSpec(BaseModel):
    module_name: str        # e.g. "accounts.py"
    class_name: str         # e.g. "Account"
    description: str        # what this module does
    key_methods: list[str]  # method signatures to implement
    dependencies: list[str] # other module_names this module depends on


class SystemDesign(BaseModel):
    system_overview: str
    modules: list[ModuleSpec]
