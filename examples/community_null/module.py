"""A locally registered package exercising the existing structural null."""

from demeter.examples.transition_modules import NoDietEffect


class CommunityNull(NoDietEffect):
    def describe(self, interface):
        return (
            super()
            .describe(interface)
            .model_copy(update={"module_id": "community.null.transitions"})
        )
