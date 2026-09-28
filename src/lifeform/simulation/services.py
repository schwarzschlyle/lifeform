from __future__ import annotations

from dataclasses import dataclass

from lifeform.biology.disease import StrainRegistry
from lifeform.biology.drives import ConditionReader, DriveCalculator, ReproductiveClock
from lifeform.biology.factory import OrganismFactory
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.phenotype import Development
from lifeform.biology.physiology import Physiology
from lifeform.cognition.affordances import AffordanceGenerator
from lifeform.cognition.decision_policy import DecisionInterpreter
from lifeform.cognition.mind_state import MindStateEncoder
from lifeform.cognition.question_panel import QuestionPanelBuilder
from lifeform.cognition.relations import RelationalFacts
from lifeform.cognition.vocabulary import RecencyWords
from lifeform.config.parameters import EcologyParameters
from lifeform.core.identifiers import IdSequence
from lifeform.core.randomness import RandomStreams
from lifeform.ecology.contests import ContestModel
from lifeform.ecology.decomposition import CarcassDecay
from lifeform.ecology.epidemiology import TransmissionModel
from lifeform.ecology.foraging import Forager
from lifeform.ecology.mating import ConceptionModel
from lifeform.ecology.mortality import MortalityJudge
from lifeform.ecology.predation import AttackModel
from lifeform.evolution.speciation import SpeciesClusterer, SpeciesRegistry
from lifeform.perception.forage_view import ForageView
from lifeform.perception.salience import DangerAssessor, SalienceRanker
from lifeform.perception.senses import HearingSense, OlfactionSense, VisionSense
from lifeform.world.world import World


@dataclass(slots=True)
class Ecosystem:
    ecology: EcologyParameters
    streams: RandomStreams
    mechanics: BodyMechanics
    clock: ReproductiveClock
    drives: DriveCalculator
    conditions: ConditionReader
    physiology: Physiology
    factory: OrganismFactory
    development: Development
    vision: VisionSense
    olfaction: OlfactionSense
    hearing: HearingSense
    forage_view: ForageView
    danger: DangerAssessor
    salience: SalienceRanker
    recency: RecencyWords
    relations: RelationalFacts
    affordances: AffordanceGenerator
    encoder: MindStateEncoder
    panels: QuestionPanelBuilder
    interpreter: DecisionInterpreter
    attacks: AttackModel
    forager: Forager
    contests: ContestModel
    conception: ConceptionModel
    strains: StrainRegistry
    transmission: TransmissionModel
    mortality: MortalityJudge
    decay: CarcassDecay
    species: SpeciesRegistry
    clusterer: SpeciesClusterer

    @classmethod
    def assemble(cls, ecology: EcologyParameters, world: World, streams: RandomStreams) -> Ecosystem:
        mechanics = BodyMechanics(ecology)
        clock = ReproductiveClock(ecology, mechanics)
        recency = RecencyWords(world.calendar)
        relations = RelationalFacts(mechanics, recency)
        development = Development(ecology, streams.stream("development"))
        danger = DangerAssessor(mechanics)
        forage_view = ForageView(mechanics)
        strains = StrainRegistry()
        species = SpeciesRegistry()
        return cls(
            ecology=ecology,
            streams=streams,
            mechanics=mechanics,
            clock=clock,
            drives=DriveCalculator(ecology, mechanics, clock),
            conditions=ConditionReader(ecology, mechanics, clock),
            physiology=Physiology(ecology, mechanics, streams.stream("physiology")),
            factory=OrganismFactory(ecology, world.metric, mechanics, streams.stream("organisms"), IdSequence()),
            development=development,
            vision=VisionSense(ecology.perception, mechanics, streams.stream("perception")),
            olfaction=OlfactionSense(mechanics),
            hearing=HearingSense(ecology.perception, mechanics, streams.stream("hearing")),
            forage_view=forage_view,
            danger=danger,
            salience=SalienceRanker(ecology.cognition, danger),
            recency=recency,
            relations=relations,
            affordances=AffordanceGenerator(ecology, mechanics, relations, recency, forage_view),
            encoder=MindStateEncoder(ecology, mechanics, relations, recency),
            panels=QuestionPanelBuilder(world.calendar.hours_per_tick, streams.stream("menu-order")),
            interpreter=DecisionInterpreter(ecology.cognition, streams.stream("decisions")),
            attacks=AttackModel(ecology.combat, mechanics, streams.stream("combat")),
            forager=Forager(ecology, mechanics, streams.stream("foraging")),
            contests=ContestModel(ecology.social, streams.stream("contests")),
            conception=ConceptionModel(ecology, mechanics, streams.stream("reproduction")),
            strains=strains,
            transmission=TransmissionModel(ecology.disease, strains, streams.stream("disease")),
            mortality=MortalityJudge(ecology, mechanics, streams.stream("mortality")),
            decay=CarcassDecay(ecology),
            species=species,
            clusterer=SpeciesClusterer(ecology.evolution, species, development),
        )
