"""Runnable extensions using only public contracts; no core engine internals."""

from demeter.contracts import (
    ModuleSpec,
    ParameterDependency,
    Quantity,
    TransitionInputs,
    TransitionInterface,
)


class DietaryTransitions:
    """Reference implementation that reproduces canonical scalar hazards."""

    def describe(self, interface: TransitionInterface) -> ModuleSpec:
        return ModuleSpec(
            module_id="example.dietary_transitions",
            version="1.0.0",
            domain="health",
            step_years=1,
            inputs=(interface.stock_port, interface.progression_port, interface.recovery_port),
            outputs=(interface.hazard_port,),
            parameters=tuple(
                ParameterDependency(key=e.parameter, unit="hazard_per_year")
                for e in interface.transitions
            ),
            equations="Base registered hazard times progression multiplier for forward edges, recovery multiplier for reverse edges",
            limitations=("Synthetic software example; not a calibrated clinical model",),
        )

    def hazards(self, inputs: TransitionInputs) -> Quantity:
        states = inputs.interface.states
        return Quantity(
            port=inputs.interface.hazard_port,
            values=tuple(
                inputs.value(edge.parameter)
                * (
                    inputs.progression.values[0]
                    if states.index(edge.target) > states.index(edge.source)
                    else inputs.recovery.values[0]
                )
                for edge in inputs.interface.transitions
            ),
        )


class NoDietEffect(DietaryTransitions):
    """Alternative hypothesis: dietary response does not modify any transition."""

    def describe(self, interface: TransitionInterface) -> ModuleSpec:
        return (
            super()
            .describe(interface)
            .model_copy(
                update={
                    "module_id": "example.no_diet_effect",
                    "equations": "Each hazard equals its registered baseline value; no dietary modifier",
                    "limitations": (
                        "Structural null for software experiments; not evidence that diet has zero clinical effect",
                    ),
                }
            )
        )

    def hazards(self, inputs: TransitionInputs) -> Quantity:
        return Quantity(
            port=inputs.interface.hazard_port,
            values=tuple(inputs.value(edge.parameter) for edge in inputs.interface.transitions),
        )
