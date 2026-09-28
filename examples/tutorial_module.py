"""Copy this file to examples/my_module.py for the module-authoring exercise."""

from demeter.contracts import Quantity, TransitionInputs, TransitionInterface, ModuleSpec
from demeter.examples.transition_modules import DietaryTransitions


class LearningNull(DietaryTransitions):
    """Practice the already-supported no-diet-effect structural hypothesis."""

    def describe(self, interface: TransitionInterface) -> ModuleSpec:
        spec = super().describe(interface)
        return spec.model_copy(
            update={
                "module_id": "tutorial.learning_null",
                "equations": "Registered baseline hazards; dietary modifiers ignored",
                "limitations": ("Teaching null hypothesis, not clinical evidence of no effect",),
            }
        )

    def hazards(self, inputs: TransitionInputs) -> Quantity:
        # The engine owns mortality, competing flows and conservation.
        # We supply one baseline hazard for each declared transition.
        return Quantity(
            port=inputs.interface.hazard_port,
            values=tuple(inputs.value(edge.parameter) for edge in inputs.interface.transitions),
        )
