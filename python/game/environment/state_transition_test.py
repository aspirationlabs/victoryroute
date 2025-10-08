"""Tests for state transition logic."""

import unittest

from absl.testing import parameterized

from python.game.environment.state_transition import StateTransition
from python.game.events.battle_event import (
    BoostEvent,
    ClearAllBoostEvent,
    ClearBoostEvent,
    ClearNegativeBoostEvent,
    CureStatusEvent,
    DamageEvent,
    DetailsChangeEvent,
    DragEvent,
    FaintEvent,
    FieldStartEvent,
    HealEvent,
    ReplaceEvent,
    SetBoostEvent,
    SetHpEvent,
    StatusEvent,
    SwitchEvent,
    UnboostEvent,
    UpkeepEvent,
    WeatherEvent,
)
from python.game.schema.battle_state import BattleState
from python.game.schema.enums import Stat, Status, Terrain, Weather
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class StateTransitionTest(parameterized.TestCase):
    """Test state transition handlers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.pikachu = PokemonState(
            species="Pikachu",
            level=100,
            current_hp=100,
            max_hp=100,
            status=Status.NONE,
            is_active=True,
        )
        self.p1_team = TeamState(pokemon=[self.pikachu], active_pokemon_index=0)
        self.initial_state = BattleState(p1_team=self.p1_team, p2_team=TeamState())

    @parameterized.parameters(
        (100, 80, 80, None, Status.NONE),
        (100, 50, 50, None, Status.NONE),
        (80, 0, 0, None, Status.NONE),
        (100, 75, 75, "brn", Status.BURN),
        (50, 25, 25, "par", Status.PARALYSIS),
        (100, 90, 90, "psn", Status.POISON),
        (100, 85, 85, "tox", Status.TOXIC),
        (100, 60, 60, "slp", Status.SLEEP),
        (100, 70, 70, "frz", Status.FREEZE),
    )
    def test_apply_damage(
        self,
        initial_hp: int,
        damage_hp: int,
        expected_hp: int,
        status_str: str,
        expected_status: Status,
    ) -> None:
        """Test damage event application."""
        pokemon = PokemonState(
            species="Pikachu", current_hp=initial_hp, max_hp=100, is_active=True
        )
        team = TeamState(pokemon=[pokemon], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = DamageEvent(
            raw_message="|damage|p1a: Pikachu|80/100",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            hp_current=damage_hp,
            hp_max=100,
            status=status_str,
        )

        new_state = StateTransition.apply(state, event)
        self.assertEqual(state.p1_team.get_active_pokemon().current_hp, initial_hp)

        new_pokemon = new_state.p1_team.get_active_pokemon()
        self.assertEqual(new_pokemon.current_hp, expected_hp)
        self.assertEqual(new_pokemon.status, expected_status)

    def test_apply_damage_preserves_status_when_not_provided(self) -> None:
        """Test that damage preserves existing status when event doesn't specify one."""
        pokemon = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            status=Status.BURN,
            is_active=True,
        )
        team = TeamState(pokemon=[pokemon], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = DamageEvent(
            raw_message="|damage|p1a: Pikachu|50/100",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            hp_current=50,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(state, event)

        new_pokemon = new_state.p1_team.get_active_pokemon()
        self.assertEqual(new_pokemon.current_hp, 50)
        self.assertEqual(new_pokemon.status, Status.BURN)

    @parameterized.parameters(
        # (initial_hp, heal_hp, expected_hp, status_str, expected_status)
        (50, 75, 75, None, Status.NONE),
        (25, 50, 50, None, Status.NONE),
        (80, 100, 100, None, Status.NONE),
        (60, 110, 100, None, Status.NONE),  # Heal capped at max
        (40, 60, 60, "", Status.NONE),  # Status cured
        (50, 75, 75, "brn", Status.BURN),
        (30, 50, 50, "par", Status.PARALYSIS),
    )
    def test_apply_heal(
        self,
        initial_hp: int,
        heal_hp: int,
        expected_hp: int,
        status_str: str,
        expected_status: Status,
    ) -> None:
        """Test heal event application."""
        pokemon = PokemonState(
            species="Pikachu",
            current_hp=initial_hp,
            max_hp=100,
            status=Status.NONE,
            is_active=True,
        )
        team = TeamState(pokemon=[pokemon], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = HealEvent(
            raw_message="|heal|p1a: Pikachu|75/100",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            hp_current=heal_hp,
            hp_max=100,
            status=status_str,
        )

        new_state = StateTransition.apply(state, event)

        self.assertEqual(state.p1_team.get_active_pokemon().current_hp, initial_hp)

        new_pokemon = new_state.p1_team.get_active_pokemon()
        self.assertEqual(new_pokemon.current_hp, expected_hp)
        self.assertEqual(new_pokemon.status, expected_status)

    @parameterized.parameters(
        # (initial_hp, set_hp, expected_hp, status_str, expected_status)
        (100, 50, 50, None, Status.NONE),
        (50, 100, 100, None, Status.NONE),
        (75, 25, 25, "brn", Status.BURN),
        (100, 1, 1, None, Status.NONE),
        (100, 0, 0, None, Status.NONE),
        (50, 75, 75, "", Status.NONE),
    )
    def test_apply_sethp(
        self,
        initial_hp: int,
        set_hp: int,
        expected_hp: int,
        status_str: str,
        expected_status: Status,
    ) -> None:
        """Test SetHp event application."""
        pokemon = PokemonState(
            species="Pikachu", current_hp=initial_hp, max_hp=100, is_active=True
        )
        team = TeamState(pokemon=[pokemon], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = SetHpEvent(
            raw_message="|sethp|p1a: Pikachu|50/100",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            hp_current=set_hp,
            hp_max=100,
            status=status_str,
        )

        new_state = StateTransition.apply(state, event)
        self.assertEqual(state.p1_team.get_active_pokemon().current_hp, initial_hp)

        new_pokemon = new_state.p1_team.get_active_pokemon()
        self.assertEqual(new_pokemon.current_hp, expected_hp)
        self.assertEqual(new_pokemon.status, expected_status)

    def test_immutability_on_damage(self) -> None:
        """Verify that applying damage doesn't mutate original state."""
        event = DamageEvent(
            raw_message="|damage|p1a: Pikachu|50/100",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            hp_current=50,
            hp_max=100,
            status=None,
        )

        original_hp = self.initial_state.p1_team.get_active_pokemon().current_hp
        original_id = id(self.initial_state)

        new_state = StateTransition.apply(self.initial_state, event)

        self.assertEqual(
            self.initial_state.p1_team.get_active_pokemon().current_hp, original_hp
        )
        self.assertEqual(id(self.initial_state), original_id)

        self.assertNotEqual(id(new_state), original_id)
        self.assertEqual(new_state.p1_team.get_active_pokemon().current_hp, 50)

    def test_player_id_routing(self) -> None:
        """Verify events are routed to correct player."""
        charizard = PokemonState(
            species="Charizard", current_hp=100, max_hp=100, is_active=True
        )
        p2_team = TeamState(pokemon=[charizard], active_pokemon_index=0)

        state = BattleState(p1_team=self.p1_team, p2_team=p2_team)

        event = DamageEvent(
            raw_message="|damage|p2a: Charizard|60/100",
            player_id="p2",
            position="a",
            pokemon_name="Charizard",
            hp_current=60,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(state, event)

        self.assertEqual(new_state.p1_team.get_active_pokemon().current_hp, 100)
        self.assertEqual(new_state.p2_team.get_active_pokemon().current_hp, 60)

    @parameterized.parameters(
        # (species, level, gender, hp_current, hp_max, status, expected_volatiles_cleared)
        ("Charizard", 100, "M", 100, 100, None, True),
        ("Garchomp", 100, "F", 85, 100, "brn", True),
        ("Landorus-Therian", 100, None, 90, 100, None, True),
    )
    def test_apply_switch(
        self,
        species: str,
        level: int,
        gender: str,
        hp_current: int,
        hp_max: int,
        status: str,
        expected_volatiles_cleared: bool,
    ) -> None:
        """Test switch event application."""
        event = SwitchEvent(
            raw_message=f"|switch|p1a: {species}|{species}, L{level}|{hp_current}/{hp_max}",
            player_id="p1",
            position="a",
            pokemon_name=species,
            species=species,
            level=level,
            gender=gender,
            shiny=False,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )

        new_state = StateTransition.apply(self.initial_state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.species, species)
        self.assertEqual(active.level, level)
        self.assertEqual(active.gender, gender)
        self.assertEqual(active.current_hp, hp_current)
        self.assertEqual(active.max_hp, hp_max)

        if expected_volatiles_cleared:
            self.assertEqual(active.volatile_conditions, {})

    def test_apply_drag(self) -> None:
        """Test drag (forced switch) event."""
        event = DragEvent(
            raw_message="|drag|p1a: Garchomp|Garchomp, L100|90/100",
            player_id="p1",
            position="a",
            pokemon_name="Garchomp",
            species="Garchomp",
            level=100,
            gender=None,
            shiny=False,
            hp_current=90,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(self.initial_state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.species, "Garchomp")
        self.assertEqual(active.current_hp, 90)
        self.assertEqual(active.volatile_conditions, {})

    def test_apply_faint(self) -> None:
        """Test faint event."""
        event = FaintEvent(
            raw_message="|faint|p1a: Pikachu",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
        )

        new_state = StateTransition.apply(self.initial_state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.current_hp, 0)
        self.assertFalse(active.is_alive())

    @parameterized.parameters(
        # (new_species, new_level, new_hp, new_status)
        ("Zoroark", 100, 80, None),
        ("Zacian-Crowned", 100, 90, "brn"),
    )
    def test_apply_replace(
        self, new_species: str, new_level: int, new_hp: int, new_status: str
    ) -> None:
        """Test replace event (Illusion break)."""
        event = ReplaceEvent(
            raw_message=f"|replace|p1a: {new_species}|{new_species}|{new_hp}/100",
            player_id="p1",
            position="a",
            pokemon_name=new_species,
            species=new_species,
            level=new_level,
            gender=None,
            shiny=False,
            hp_current=new_hp,
            hp_max=100,
            status=new_status,
        )

        new_state = StateTransition.apply(self.initial_state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.species, new_species)
        self.assertEqual(active.current_hp, new_hp)

    def test_apply_replace_preserves_status_when_not_provided(self) -> None:
        """Test that replace preserves existing status when event doesn't specify one."""
        pokemon = PokemonState(
            species="Zoroark",
            current_hp=80,
            max_hp=100,
            status=Status.PARALYSIS,
            is_active=True,
        )
        team = TeamState(pokemon=[pokemon], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = ReplaceEvent(
            raw_message="|replace|p1a: Zoroark|Zoroark|80/100",
            player_id="p1",
            position="a",
            pokemon_name="Zoroark",
            species="Zoroark",
            level=100,
            gender=None,
            shiny=False,
            hp_current=80,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.species, "Zoroark")
        self.assertEqual(active.current_hp, 80)
        self.assertEqual(active.status, Status.PARALYSIS)

    @parameterized.parameters(
        # (new_details, expected_species, expected_level)
        ("Darmanitan-Zen, L100", "Darmanitan-Zen", 100),
        ("Aegislash-Blade, L50", "Aegislash-Blade", 50),
    )
    def test_apply_details_change(
        self, new_details: str, expected_species: str, expected_level: int
    ) -> None:
        """Test details change event (forme change)."""
        event = DetailsChangeEvent(
            raw_message=f"|detailschange|p1a: {expected_species}|{new_details}|100/100",
            player_id="p1",
            position="a",
            pokemon_name=expected_species,
            new_details=new_details,
            hp_current=100,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(self.initial_state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.species, expected_species)
        self.assertEqual(active.level, expected_level)

    def test_volatiles_cleared_on_switch(self) -> None:
        """Verify volatile conditions are cleared when switching."""
        pokemon_with_volatiles = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            volatile_conditions={"confusion": 3, "taunt": 2},
            is_active=True,
        )
        team = TeamState(pokemon=[pokemon_with_volatiles], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = SwitchEvent(
            raw_message="|switch|p1a: Garchomp|Garchomp|100/100",
            player_id="p1",
            position="a",
            pokemon_name="Garchomp",
            species="Garchomp",
            level=100,
            gender=None,
            shiny=False,
            hp_current=100,
            hp_max=100,
            status=None,
        )

        new_state = StateTransition.apply(state, event)

        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.volatile_conditions, {})

    @parameterized.parameters(
        ("atk", 1, 1),
        ("def", 2, 2),
        ("spe", 1, 1),
        ("atk", 7, 6),  # Clamped to +6
        ("def", -8, -6),  # Clamped to -6
    )
    def test_apply_boost(
        self, stat_name: str, amount: int, expected_stage: int
    ) -> None:
        """Test stat boost application."""
        event = BoostEvent(
            raw_message=f"|boost|p1a: Pikachu|{stat_name}|{amount}",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            stat=stat_name,
            amount=amount,
        )

        new_state = StateTransition.apply(self.initial_state, event)
        active = new_state.p1_team.get_active_pokemon()

        stat_enum = StateTransition._parse_stat(stat_name)
        self.assertEqual(active.stat_boosts.get(stat_enum, 0), expected_stage)

    @parameterized.parameters(
        ("atk", 1, -1),
        ("def", 2, -2),
        ("spe", 1, -1),
    )
    def test_apply_unboost(
        self, stat_name: str, amount: int, expected_stage: int
    ) -> None:
        """Test stat decrease application."""
        event = UnboostEvent(
            raw_message=f"|unboost|p1a: Pikachu|{stat_name}|{amount}",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            stat=stat_name,
            amount=amount,
        )

        new_state = StateTransition.apply(self.initial_state, event)
        active = new_state.p1_team.get_active_pokemon()

        stat_enum = StateTransition._parse_stat(stat_name)
        self.assertEqual(active.stat_boosts.get(stat_enum, 0), expected_stage)

    def test_apply_setboost(self) -> None:
        """Test setting stat to specific stage."""
        event = SetBoostEvent(
            raw_message="|setboost|p1a: Pikachu|atk|3",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            stat="atk",
            stage=3,
        )

        new_state = StateTransition.apply(self.initial_state, event)
        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.stat_boosts.get(Stat.ATK, 0), 3)

    def test_apply_clearboost(self) -> None:
        """Test clearing all stat boosts."""
        pikachu_with_boosts = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            stat_boosts={Stat.ATK: 2, Stat.DEF: 1},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu_with_boosts], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = ClearBoostEvent(
            raw_message="|clearboost|p1a: Pikachu",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
        )

        new_state = StateTransition.apply(state, event)
        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.stat_boosts, {})

    def test_apply_clearallboost(self) -> None:
        """Test clearing all boosts for all pokemon (Haze)."""
        p1_pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            stat_boosts={Stat.ATK: 2},
            is_active=True,
        )
        p2_charizard = PokemonState(
            species="Charizard",
            current_hp=100,
            max_hp=100,
            stat_boosts={Stat.DEF: -1},
            is_active=True,
        )

        state = BattleState(
            p1_team=TeamState(pokemon=[p1_pikachu], active_pokemon_index=0),
            p2_team=TeamState(pokemon=[p2_charizard], active_pokemon_index=0),
        )

        event = ClearAllBoostEvent(raw_message="|clearallboost")

        new_state = StateTransition.apply(state, event)

        self.assertEqual(new_state.p1_team.get_active_pokemon().stat_boosts, {})
        self.assertEqual(new_state.p2_team.get_active_pokemon().stat_boosts, {})

    def test_apply_clearnegativeboost(self) -> None:
        """Test clearing only negative boosts."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            stat_boosts={Stat.ATK: 2, Stat.DEF: -1, Stat.SPE: -2},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = ClearNegativeBoostEvent(
            raw_message="|clearnegativeboost|p1a: Pikachu",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
        )

        new_state = StateTransition.apply(state, event)
        active = new_state.p1_team.get_active_pokemon()

        self.assertEqual(active.stat_boosts, {Stat.ATK: 2})

    @parameterized.parameters(
        ("brn", Status.BURN),
        ("par", Status.PARALYSIS),
        ("psn", Status.POISON),
        ("tox", Status.TOXIC),
        ("slp", Status.SLEEP),
        ("frz", Status.FREEZE),
    )
    def test_apply_status(self, status_str: str, expected_status: Status) -> None:
        """Test status application."""
        event = StatusEvent(
            raw_message=f"|status|p1a: Pikachu|{status_str}",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            status=status_str,
        )

        new_state = StateTransition.apply(self.initial_state, event)
        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.status, expected_status)

    def test_apply_curestatus(self) -> None:
        """Test status cure."""
        pikachu_burned = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            status=Status.BURN,
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu_burned], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = CureStatusEvent(
            raw_message="|curestatus|p1a: Pikachu|brn",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            status="brn",
        )

        new_state = StateTransition.apply(state, event)
        active = new_state.p1_team.get_active_pokemon()
        self.assertEqual(active.status, Status.NONE)

    def test_apply_switch_preserves_tera_type(self) -> None:
        """Test that switch preserves tera type when Pokemon is terastallized."""
        pikachu_tera = PokemonState(
            species="Pikachu",
            level=50,
            current_hp=100,
            max_hp=120,
            status=Status.NONE,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
            ],
            item="Light Ball",
            ability="Lightning Rod",
            tera_type="Electric",
            has_terastallized=True,
            stat_boosts={Stat.SPE: 1},
            is_active=False,
        )
        team = TeamState(pokemon=[pikachu_tera], active_pokemon_index=None)
        state = BattleState(p1_team=team, p2_team=TeamState())

        event = SwitchEvent(
            raw_message="|switch|p1a: Pikachu|Pikachu, L50|100/120",
            player_id="p1",
            position="a",
            pokemon_name="Pikachu",
            species="Pikachu",
            level=50,
            gender=None,
            shiny=False,
            hp_current=100,
            hp_max=120,
            status=None,
        )

        new_state = StateTransition.apply(state, event)
        active = new_state.p1_team.get_active_pokemon()

        self.assertEqual(active.tera_type, "Electric")
        self.assertTrue(active.has_terastallized)

        self.assertEqual(len(active.moves), 2)
        self.assertEqual(active.moves[0].name, "Thunderbolt")
        self.assertEqual(active.item, "Light Ball")
        self.assertEqual(active.ability, "Lightning Rod")

        self.assertEqual(active.stat_boosts, {})

        self.assertEqual(active.volatile_conditions, {})

    def test_apply_upkeep_decrements_terrain(self) -> None:
        """Test that upkeep decrements terrain turns."""
        field_event = FieldStartEvent(
            raw_message="|-fieldstart|move: grassy terrain",
            effect="Grassy Terrain",
        )
        state = StateTransition.apply(self.initial_state, field_event)

        self.assertEqual(state.field_state.terrain, Terrain.GRASSY)
        self.assertEqual(state.field_state.terrain_turns_remaining, 5)

        upkeep_event = UpkeepEvent(raw_message="|upkeep")
        state = StateTransition.apply(state, upkeep_event)
        self.assertEqual(state.field_state.terrain_turns_remaining, 4)

        state = StateTransition.apply(state, upkeep_event)
        self.assertEqual(state.field_state.terrain_turns_remaining, 3)

    def test_apply_upkeep_decrements_weather(self) -> None:
        """Test that upkeep decrements weather turns."""
        weather_event = WeatherEvent(
            raw_message="|-weather|rain", weather="Rain", upkeep=False
        )
        state = StateTransition.apply(self.initial_state, weather_event)

        self.assertEqual(state.field_state.weather, Weather.RAIN)
        self.assertEqual(state.field_state.weather_turns_remaining, 5)

        upkeep_event = UpkeepEvent(raw_message="|upkeep")
        state = StateTransition.apply(state, upkeep_event)
        self.assertEqual(state.field_state.weather_turns_remaining, 4)

        state = StateTransition.apply(state, upkeep_event)
        self.assertEqual(state.field_state.weather_turns_remaining, 3)

    def test_apply_player_event_p1(self) -> None:
        """Test that PlayerEvent updates p1_username."""
        from python.game.events.battle_event import PlayerEvent

        event = PlayerEvent(
            raw_message="|player|p1|Alice|1|1500",
            player_id="p1",
            username="Alice",
            avatar="1",
            rating=1500,
        )
        state = StateTransition.apply(self.initial_state, event)
        self.assertEqual(state.p1_username, "Alice")
        self.assertIsNone(state.p2_username)

    def test_apply_player_event_p2(self) -> None:
        """Test that PlayerEvent updates p2_username."""
        from python.game.events.battle_event import PlayerEvent

        event = PlayerEvent(
            raw_message="|player|p2|Bob|2|1400",
            player_id="p2",
            username="Bob",
            avatar="2",
            rating=1400,
        )
        state = StateTransition.apply(self.initial_state, event)
        self.assertIsNone(state.p1_username)
        self.assertEqual(state.p2_username, "Bob")

    def test_apply_battle_end_victory(self) -> None:
        """Test that BattleEndEvent marks battle as over with winner."""
        from python.game.events.battle_event import BattleEndEvent

        event = BattleEndEvent(raw_message="|win|Alice", winner="Alice")
        state = StateTransition.apply(self.initial_state, event)
        self.assertTrue(state.battle_over)
        self.assertEqual(state.winner, "Alice")

    def test_apply_battle_end_tie(self) -> None:
        """Test that tie marks battle as over with no winner."""
        from python.game.events.battle_event import BattleEndEvent

        event = BattleEndEvent(raw_message="|tie", winner="")
        state = StateTransition.apply(self.initial_state, event)
        self.assertTrue(state.battle_over)
        self.assertEqual(state.winner, "")

    def test_apply_request_with_wait(self) -> None:
        """Test that wait requests maintain current state."""
        from python.game.events.battle_event import RequestEvent

        initial_state = BattleState(
            available_moves=["Move1", "Move2"],
            available_switches=[1, 2],
        )

        event = RequestEvent(
            raw_message='|request|{"wait":true}', request_json='{"wait":true}'
        )
        new_state = StateTransition.apply(initial_state, event)

        self.assertEqual(new_state, initial_state)
        self.assertEqual(["Move1", "Move2"], new_state.available_moves)
        self.assertEqual([1, 2], new_state.available_switches)


if __name__ == "__main__":
    unittest.main()
