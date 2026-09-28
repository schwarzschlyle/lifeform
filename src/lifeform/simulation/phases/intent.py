from __future__ import annotations

from lifeform.simulation.context import TickContext


class IntentPhase:
    name = "intent"

    def run(self, context: TickContext) -> None:
        interpreter = context.services.interpreter
        for organism in context.population.living():
            decision = context.decisions.get(organism.id)
            panel = context.panels.get(organism.id)
            if decision is None or panel is None:
                context.intents[organism.id] = interpreter.stalled(organism)
                continue
            intent = interpreter.interpret(organism, panel, decision)
            interpreter.appraise_fear(organism, decision.threat.score)
            context.intents[organism.id] = intent
        context.persistent.last_intents = dict(context.intents)
