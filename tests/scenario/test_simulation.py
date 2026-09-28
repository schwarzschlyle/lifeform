from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lifeform.adapters.offline import HeuristicBrain, ScriptedBrain
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import QuestionPanel
from lifeform.config.parameters import CognitionParameters
from lifeform.config.run_config import RecordingSettings
from lifeform.recording.chunks import read_packed
from lifeform.recording.world_recorder import WorldRecorder
from lifeform.simulation.engine import Simulation
from lifeform.simulation.phases.deliberation import DeliberationOptions
from lifeform.simulation.world_factory import BuiltWorld

DECIMAL_NUMBER = re.compile(r"\d+\.\d+")


def choose_rest(_: MindState, panel: QuestionPanel) -> str:
    keys = [affordance.key for affordance in panel.menu]
    return "rest" if "rest" in keys else keys[0]


@pytest.mark.asyncio
async def test_every_living_animal_gets_exactly_one_call_per_tick(small_world: BuiltWorld) -> None:
    brain = ScriptedBrain(choose_rest)
    simulation = Simulation(small_world, brain, DeliberationOptions())
    expected = 0
    for _ in range(4):
        expected += len(simulation.population)
        context = await simulation.advance()
        assert set(context.decisions) == set(context.minds)
    assert brain.calls == expected


@pytest.mark.asyncio
async def test_states_are_words_and_menus_are_legal(small_world: BuiltWorld) -> None:
    simulation = Simulation(small_world, HeuristicBrain(), DeliberationOptions())
    limit = CognitionParameters().max_menu_options
    for _ in range(3):
        context = await simulation.advance()
        for organism_id, mind in context.minds.items():
            panel = context.panels[organism_id]
            assert not DECIMAL_NUMBER.search(mind.to_json()), "raw numbers must never reach Jev"
            assert 0 < len(panel.menu) <= limit
            assert len({affordance.key for affordance in panel.menu}) == len(panel.menu)
            assert context.intents[organism_id].sampled_key in {affordance.key for affordance in panel.menu}
            assert "silent" in panel.call.criteria


@pytest.mark.asyncio
async def test_recording_writes_a_replayable_bundle(small_world: BuiltWorld, tmp_path: Path) -> None:
    simulation = Simulation(small_world, HeuristicBrain(), DeliberationOptions())
    recorder = WorldRecorder(tmp_path, simulation, RecordingSettings(chunk_ticks=4), "heuristic")
    simulation.observe(recorder)
    recorder.start()
    for _ in range(6):
        await simulation.advance()
    recorder.finish("complete")
    index = json.loads((tmp_path / "index.json").read_text())
    frames = [frame for _, _, path in index["frames"] for frame in read_packed(tmp_path / path)]
    assert [frame["tick"] for frame in frames] == list(range(7))
    assert json.loads((tmp_path / "world.json").read_text())["status"] == "complete"
    decisions = read_packed(tmp_path / index["decisions"][0][2])
    assert decisions[0]["decisions"][0]["state"]["task"]
