"""Integration tests for BattleState based on real battle logs."""

import json
import unittest

from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.enums import (
    FieldEffect,
    SideCondition,
    Stat,
    Status,
    Weather,
)
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class BattleStateTest(unittest.IsolatedAsyncioTestCase):
    """Test BattleState with scenarios from real battle logs."""

    def test_stealth_rock_plus_intimidate(self) -> None:
        """Test Case 1: Battle 1 Turn 3 - Stealth Rock + Intimidate.

        Scenario from logs:
        - P1 has Stealth Rock active
        - P2's Gholdengo has -1 Atk from Intimidate
        """
        p1_pokemon = [PokemonState(species="Iron Crown", current_hp=94, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        p2_pokemon = [
            PokemonState(
                species="Gholdengo",
                current_hp=81,
                max_hp=100,
                stat_boosts={Stat.ATK: -1},  # From Intimidate
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=3)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["p1_side_conditions"]["stealthrock"], 1)
        self.assertEqual(len(field_info["p2_side_conditions"]), 0)

        gholdengo = battle.get_active_pokemon("p2")
        self.assertIsNotNone(gholdengo)
        base_stats = {Stat.ATK: 85}
        stats = battle.get_pokemon_battle_state(gholdengo, base_stats)  # type: ignore
        # Base 85 Atk with -1 stage = 85 * (2/3) = 56.67 -> 56
        self.assertEqual(stats["atk"], 56)

    def test_future_sight_plus_entry_hazards(self) -> None:
        """Test Case 2: Battle 1 Turn 10 - Future Sight + Entry Hazards.

        Scenario from logs (lines ~150):
        - Both sides have Stealth Rock
        - P1 has Future Sight pending
        """
        p1_pokemon = [PokemonState(species="Iron Crown", current_hp=58, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        p2_pokemon = [PokemonState(species="Gholdengo", current_hp=50, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        field = FieldState(turn_number=10)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["p1_side_conditions"]["stealthrock"], 1)
        self.assertEqual(field_info["p2_side_conditions"]["stealthrock"], 1)

    def test_burn_plus_leftovers(self) -> None:
        """Test Case 3: Battle 1 Turn 20 - Burn Status + Leftovers healing.

        Scenario from logs (lines ~294):
        - Raging Bolt burned status
        - Rotom has Leftovers healing
        """
        p1_pokemon = [
            PokemonState(
                species="Raging Bolt",
                current_hp=56,
                max_hp=100,
                status=Status.BURN,
            )
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        p2_pokemon = [
            PokemonState(
                species="Rotom-Wash", current_hp=20, max_hp=100, item="Leftovers"
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=20)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        raging_bolt = battle.get_active_pokemon("p1")
        self.assertIsNotNone(raging_bolt)
        stats = battle.get_pokemon_battle_state(raging_bolt)  # type: ignore
        self.assertEqual(stats["status"], "brn")
        self.assertEqual(stats["hp"]["percentage"], 56.0)

    def test_terastallization_plus_supreme_overlord(self) -> None:
        """Test Case 4: Battle 1 Turn 24 - Terastallize + Supreme Overlord.

        Scenario from logs (lines ~350):
        - Kingambit terastallized to Fairy
        - Supreme Overlord with fallen4 (4 fainted teammates)
        """
        p2_pokemon = [
            PokemonState(
                species="Kingambit",
                current_hp=74,
                max_hp=100,
                has_terastallized=True,
                tera_type="Fairy",
                active_effects={"supreme_overlord_fallen": 4},
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [PokemonState(species="Zamazenta", current_hp=37, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=24)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        kingambit = battle.get_active_pokemon("p2")
        self.assertIsNotNone(kingambit)
        stats = battle.get_pokemon_battle_state(kingambit)  # type: ignore
        self.assertTrue(kingambit.has_terastallized)  # type: ignore
        self.assertEqual(kingambit.tera_type, "Fairy")  # type: ignore
        self.assertEqual(stats["supreme_overlord_fallen"], 4)

    def test_protect_plus_poison_heal(self) -> None:
        """Test Case 5: Battle 2 Turn 3 - Protect + Poison Heal.

        Scenario from logs (lines ~479):
        - Gliscor with Protect active (volatile)
        - Toxic Orb poisoned + Poison Heal ability
        """
        p1_pokemon = [
            PokemonState(
                species="Gliscor",
                current_hp=72,
                max_hp=100,
                status=Status.TOXIC,
                ability="Poison Heal",
                item="Toxic Orb",
                volatile_conditions={"protect_count": 1},
            )
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        p2_pokemon = [PokemonState(species="Glimmora", current_hp=73, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=3)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        gliscor = battle.get_active_pokemon("p1")
        self.assertIsNotNone(gliscor)
        stats = battle.get_pokemon_battle_state(gliscor)  # type: ignore
        self.assertEqual(stats["status"], "tox")
        self.assertEqual(stats["protect_count"], 1)

    def test_light_screen_plus_reflect(self) -> None:
        """Test Case 6: Battle 7 Turns 3-4 - Light Screen + Reflect combo.

        Scenario from logs (lines 2732-2743):
        - Both screens active on P1's side with turns remaining
        """
        p1_pokemon = [PokemonState(species="Deoxys", current_hp=11, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={
                SideCondition.LIGHT_SCREEN: 5,
                SideCondition.REFLECT: 5,
            },
        )

        p2_pokemon = [PokemonState(species="Darkrai", current_hp=100, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=4)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["p1_side_conditions"]["lightscreen"], 5)
        self.assertEqual(field_info["p1_side_conditions"]["reflect"], 5)

    def test_multiple_calm_minds(self) -> None:
        """Test Case 7: Battle 5 Turns 33-36 - Multiple Calm Mind boosts.

        Scenario from logs (lines 2185-2217):
        - Raging Bolt: +3 SpA, +3 SpD after 3x Calm Mind
        - Then uses Draco Meteor: -2 SpA
        - Final state: +1 SpA, +3 SpD, burned
        """
        p2_pokemon = [
            PokemonState(
                species="Raging Bolt",
                current_hp=82,
                max_hp=100,
                status=Status.BURN,
                stat_boosts={Stat.SPA: 1, Stat.SPD: 3},  # After Draco Meteor
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [PokemonState(species="Dondozo", current_hp=56, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=37)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        raging_bolt = battle.get_active_pokemon("p2")
        self.assertIsNotNone(raging_bolt)

        base_stats = {Stat.SPA: 137, Stat.SPD: 113}
        stats = battle.get_pokemon_battle_state(raging_bolt, base_stats)  # type: ignore

        # +1 SpA: 137 * 1.5 = 205.5 -> 205
        self.assertEqual(stats["spa"], 205)
        # +3 SpD: 113 * 2.5 = 282.5 -> 282
        self.assertEqual(stats["spd"], 282)
        self.assertEqual(stats["status"], "brn")

    def test_snow_weather(self) -> None:
        """Test Case 8: Battle 2 Turn 16 - Snow weather from Snow Warning.

        Scenario from logs (lines ~612):
        - Snow from Snow Warning ability
        """
        p2_pokemon = [
            PokemonState(
                species="Ninetales-Alola",
                current_hp=44,
                max_hp=100,
                ability="Snow Warning",
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [PokemonState(species="Dondozo", current_hp=72, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(
            weather=Weather.SNOW, weather_turns_remaining=5, turn_number=16
        )

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["weather"], "snow")
        self.assertEqual(field_info["weather_turns_remaining"], 5)

    def test_dragon_dance(self) -> None:
        """Test Case 9: Battle 2 Turn 22 - Dragon Dance stat boosts.

        Scenario from logs (lines ~687):
        - Dragonite with +1 Atk, +1 Spe from Dragon Dance
        """
        p2_pokemon = [
            PokemonState(
                species="Roaring Moon",
                current_hp=82,
                max_hp=100,
                stat_boosts={Stat.ATK: 1, Stat.SPE: 1},
            )
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [PokemonState(species="Toxapex", current_hp=28, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=22)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        roaring_moon = battle.get_active_pokemon("p2")
        self.assertIsNotNone(roaring_moon)

        base_stats = {Stat.ATK: 139, Stat.SPE: 119}
        stats = battle.get_pokemon_battle_state(roaring_moon, base_stats)  # type: ignore

        # +1 Atk: 139 * 1.5 = 208.5 -> 208
        self.assertEqual(stats["atk"], 208)
        # +1 Spe: 119 * 1.5 = 178.5 -> 178
        self.assertEqual(stats["spe"], 178)

    def test_tailwind(self) -> None:
        """Test Case 10: Line 71646 - Tailwind side condition."""
        p1_pokemon = [PokemonState(species="Ribombee", current_hp=100, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.TAILWIND: 4},
        )

        p2_pokemon = [PokemonState(species="Kingambit", current_hp=100, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=10)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["p1_side_conditions"]["tailwind"], 4)

    def test_trick_room(self) -> None:
        """Test Case 11: Line 23544 - Trick Room field effect."""
        p2_pokemon = [PokemonState(species="Hatterene", current_hp=100, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [PokemonState(species="Cinderace", current_hp=80, max_hp=100)]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(
            field_effects=[FieldEffect.TRICK_ROOM],
            field_effect_turns_remaining={FieldEffect.TRICK_ROOM: 4},
            turn_number=15,
        )

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertIn("trickroom", field_info["field_effects"])
        self.assertTrue(battle.field_state.has_field_effect(FieldEffect.TRICK_ROOM))

    def test_sleep_from_rest(self) -> None:
        """Test Case 12: Battle 2 Turn 27 - Sleep from Rest + Curse stat changes.

        Scenario from logs (lines ~756):
        - Dondozo asleep from Rest
        - Multiple stat changes from Curse
        """
        p1_pokemon = [
            PokemonState(
                species="Dondozo",
                current_hp=74,
                max_hp=100,
                status=Status.SLEEP,
                stat_boosts={Stat.ATK: 1, Stat.DEF: 1, Stat.SPE: -1},
            )
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        p2_pokemon = [PokemonState(species="Kingambit", current_hp=81, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=27)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
        )

        dondozo = battle.get_active_pokemon("p1")
        self.assertIsNotNone(dondozo)

        base_stats = {Stat.ATK: 100, Stat.DEF: 115, Stat.SPE: 35}
        stats = battle.get_pokemon_battle_state(dondozo, base_stats)  # type: ignore

        self.assertEqual(stats["status"], "slp")
        # +1 Atk: 100 * 1.5 = 150
        self.assertEqual(stats["atk"], 150)
        # +1 Def: 115 * 1.5 = 172.5 -> 172
        self.assertEqual(stats["def"], 172)
        # -1 Spe: 35 * (2/3) = 23.33 -> 23
        self.assertEqual(stats["spe"], 23)

    def test_infer_available_moves(self) -> None:
        """Test move inference from battle state."""
        # Create Pokemon with moves
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
                PokemonMove(name="Thunder Wave", current_pp=0, max_pp=20),  # No PP
            ],
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        # Get available moves - should exclude Thunder Wave (no PP)
        moves = state.get_available_moves("p1")
        self.assertEqual(set(moves), {"Thunderbolt", "Volt Switch"})

    def test_infer_opponent_moves_returns_empty(self) -> None:
        """Test that opponent moves return empty list once revealed.

        When the opponent uses moves (learned via MoveEvent), the server doesn't
        re-send the move list in subsequent requests. The inference should return
        an empty list to match this behavior.
        """
        # Set up our player as p1
        our_pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            is_active=True,
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        # Opponent (p2) has revealed moves from battle
        opponent_charizard = PokemonState(
            species="Charizard",
            current_hp=80,
            max_hp=100,
            moves=[
                PokemonMove(name="Flamethrower", current_pp=15, max_pp=15),
                PokemonMove(name="Air Slash", current_pp=20, max_pp=20),
            ],
            is_active=True,
        )
        opponent_team = TeamState(pokemon=[opponent_charizard], active_pokemon_index=0)

        # Create state with our_player_id set to p1
        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team},
            our_player_id="p1"
        )

        # Opponent moves should return empty (already revealed via MoveEvent)
        opponent_moves = state._infer_available_moves("p2")
        self.assertEqual(opponent_moves, [])

        # Our moves should still work normally
        our_moves = state._infer_available_moves("p1")
        self.assertEqual(our_moves, [])

    def test_infer_available_switches(self) -> None:
        """Test switch inference from battle state."""
        pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        charizard = PokemonState(species="Charizard", current_hp=80, max_hp=100)
        fainted = PokemonState(species="Blastoise", current_hp=0, max_hp=100)

        team = TeamState(pokemon=[pikachu, charizard, fainted], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        switches = state.get_available_switches("p1")
        self.assertEqual(switches, [1])

    def test_infer_available_switches_with_none_active_index(self) -> None:
        """Test switch inference when active_pokemon_index is None (team preview).

        This case occurs during team preview before any Pokemon has switched in.
        The inference should still work and not incorrectly include index 0.
        """
        pikachu = PokemonState(species="Pikachu", current_hp=100, max_hp=100)
        charizard = PokemonState(species="Charizard", current_hp=80, max_hp=100)
        blastoise = PokemonState(species="Blastoise", current_hp=100, max_hp=100)

        # active_pokemon_index is None (no Pokemon has switched in yet)
        team = TeamState(pokemon=[pikachu, charizard, blastoise], active_pokemon_index=None)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        switches = state.get_available_switches("p1")
        # All alive Pokemon should be available since none is active yet
        self.assertEqual(set(switches), {0, 1, 2})

    def test_infer_available_moves_with_encore(self) -> None:
        """Test that Encore forces only the encored move to be available."""
        # Create Pokemon with multiple moves, but Encored on Thunderbolt
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
                PokemonMove(name="Quick Attack", current_pp=10, max_pp=30),
                PokemonMove(name="Thunder Wave", current_pp=5, max_pp=20),
            ],
            volatile_conditions={"encore": {"move": "Thunderbolt"}},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        # Only Thunderbolt should be available due to Encore
        moves = state.get_available_moves("p1")
        self.assertEqual(moves, ["Thunderbolt"])

    def test_infer_available_moves_with_encore_string_format(self) -> None:
        """Test Encore with string format (backward compatibility)."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
            ],
            volatile_conditions={"encore": "Thunderbolt"},  # String format
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        moves = state.get_available_moves("p1")
        self.assertEqual(moves, ["Thunderbolt"])

    def test_infer_available_moves_with_encore_no_pp(self) -> None:
        """Test that Encore returns empty when encored move has no PP."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=0, max_pp=15),  # No PP!
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
            ],
            volatile_conditions={"encore": {"move": "Thunderbolt"}},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        # Should return empty since encored move has no PP
        moves = state.get_available_moves("p1")
        self.assertEqual(moves, [])

    def test_infer_available_moves_with_disable(self) -> None:
        """Test that Disable excludes the disabled move from available moves."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
                PokemonMove(name="Quick Attack", current_pp=10, max_pp=30),
                PokemonMove(name="Thunder Wave", current_pp=5, max_pp=20),
            ],
            volatile_conditions={"disable": {"move": "Thunderbolt"}},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        # All moves except Thunderbolt should be available
        moves = state.get_available_moves("p1")
        self.assertEqual(set(moves), {"Volt Switch", "Quick Attack", "Thunder Wave"})

    def test_infer_available_moves_with_disable_string_format(self) -> None:
        """Test Disable with string format (backward compatibility)."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
            ],
            volatile_conditions={"disable": "Thunderbolt"},  # String format
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        moves = state.get_available_moves("p1")
        self.assertEqual(moves, ["Volt Switch"])

    def test_infer_available_moves_with_disable_and_no_pp(self) -> None:
        """Test that Disable works correctly when disabled move has no PP anyway."""
        pikachu = PokemonState(
            species="Pikachu",
            current_hp=100,
            max_hp=100,
            moves=[
                PokemonMove(name="Thunderbolt", current_pp=0, max_pp=15),  # No PP
                PokemonMove(name="Volt Switch", current_pp=20, max_pp=20),
                PokemonMove(name="Quick Attack", current_pp=10, max_pp=30),
            ],
            volatile_conditions={"disable": {"move": "Thunderbolt"}},
            is_active=True,
        )
        team = TeamState(pokemon=[pikachu], active_pokemon_index=0)
        state = BattleState(teams={"p1": team, "p2": TeamState()})

        # Thunderbolt already has no PP, so same result as without Disable
        moves = state.get_available_moves("p1")
        self.assertEqual(set(moves), {"Volt Switch", "Quick Attack"})

    def test_json_serialization(self) -> None:
        """Test complete battle state JSON serialization."""
        p1_pokemon = [
            PokemonState(species="Landorus-Therian", current_hp=88, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        p2_pokemon = [PokemonState(species="Kommo-o", current_hp=100, max_hp=100)]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=1)

        battle = BattleState(
            teams={"p1": p1_team, "p2": p2_team},
            field_state=field,
            battle_format="singles",
        )

        json_str = str(battle)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["battle_format"], "singles")
        self.assertEqual(parsed["field_state"]["turn_number"], 1)
        self.assertIn("stealthrock", parsed["p1_team"]["side_conditions"])

    def test_opponent_potential_actions_no_revealed_moves(self) -> None:
        """Test opponent actions when no moves are revealed yet."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard", current_hp=80, max_hp=100, is_active=True
        )
        opponent_blastoise = PokemonState(
            species="Blastoise", current_hp=100, max_hp=100
        )
        opponent_team = TeamState(
            pokemon=[opponent_charizard, opponent_blastoise], active_pokemon_index=0
        )

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        actions = state.get_opponent_potential_actions()

        move_actions = [a for a in actions if a.action_type == ActionType.UNKNOWN_MOVE]
        switch_actions = [a for a in actions if a.action_type == ActionType.SWITCH]

        self.assertEqual(len(move_actions), 4)
        self.assertEqual(len(switch_actions), 1)
        self.assertEqual(switch_actions[0].switch_pokemon_name, "Blastoise")

    def test_opponent_potential_actions_partial_moves_revealed(self) -> None:
        """Test opponent actions when some moves are revealed."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard",
            current_hp=80,
            max_hp=100,
            moves=[
                PokemonMove(name="Flamethrower", current_pp=15, max_pp=15),
                PokemonMove(name="Air Slash", current_pp=20, max_pp=20),
            ],
            is_active=True,
        )
        opponent_blastoise = PokemonState(
            species="Blastoise", current_hp=100, max_hp=100
        )
        opponent_team = TeamState(
            pokemon=[opponent_charizard, opponent_blastoise], active_pokemon_index=0
        )

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        actions = state.get_opponent_potential_actions()

        move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
        unknown_move_actions = [
            a for a in actions if a.action_type == ActionType.UNKNOWN_MOVE
        ]
        switch_actions = [a for a in actions if a.action_type == ActionType.SWITCH]

        self.assertEqual(len(move_actions), 2)
        self.assertEqual(len(unknown_move_actions), 2)
        self.assertEqual(len(switch_actions), 1)

        move_names = {a.move_name for a in move_actions}
        self.assertEqual(move_names, {"Flamethrower", "Air Slash"})

    def test_opponent_potential_actions_all_moves_revealed(self) -> None:
        """Test opponent actions when all 4 moves are revealed."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard",
            current_hp=80,
            max_hp=100,
            moves=[
                PokemonMove(name="Flamethrower", current_pp=15, max_pp=15),
                PokemonMove(name="Air Slash", current_pp=20, max_pp=20),
                PokemonMove(name="Dragon Claw", current_pp=10, max_pp=15),
                PokemonMove(name="Roost", current_pp=5, max_pp=10),
            ],
            is_active=True,
        )
        opponent_blastoise = PokemonState(
            species="Blastoise", current_hp=100, max_hp=100
        )
        opponent_team = TeamState(
            pokemon=[opponent_charizard, opponent_blastoise], active_pokemon_index=0
        )

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        actions = state.get_opponent_potential_actions()

        move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
        unknown_move_actions = [
            a for a in actions if a.action_type == ActionType.UNKNOWN_MOVE
        ]
        switch_actions = [a for a in actions if a.action_type == ActionType.SWITCH]

        self.assertEqual(len(move_actions), 4)
        self.assertEqual(len(unknown_move_actions), 0)
        self.assertEqual(len(switch_actions), 1)

        move_names = {a.move_name for a in move_actions}
        self.assertEqual(
            move_names, {"Flamethrower", "Air Slash", "Dragon Claw", "Roost"}
        )

    def test_opponent_potential_actions_move_with_no_pp(self) -> None:
        """Test opponent actions exclude moves with 0 PP."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard",
            current_hp=80,
            max_hp=100,
            moves=[
                PokemonMove(name="Flamethrower", current_pp=0, max_pp=15),
                PokemonMove(name="Air Slash", current_pp=20, max_pp=20),
            ],
            is_active=True,
        )
        opponent_team = TeamState(pokemon=[opponent_charizard], active_pokemon_index=0)

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        actions = state.get_opponent_potential_actions()

        move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
        unknown_move_actions = [
            a for a in actions if a.action_type == ActionType.UNKNOWN_MOVE
        ]

        self.assertEqual(len(move_actions), 1)
        self.assertEqual(move_actions[0].move_name, "Air Slash")
        self.assertEqual(len(unknown_move_actions), 2)

    def test_opponent_potential_actions_team_preview(self) -> None:
        """Test opponent actions return empty during team preview."""
        our_pikachu = PokemonState(species="Pikachu", current_hp=100, max_hp=100)
        our_team = TeamState(pokemon=[our_pikachu])

        opponent_charizard = PokemonState(
            species="Charizard", current_hp=100, max_hp=100
        )
        opponent_team = TeamState(pokemon=[opponent_charizard])

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team},
            our_player_id="p1",
            team_preview=True,
        )

        actions = state.get_opponent_potential_actions()
        self.assertEqual(len(actions), 0)

    def test_opponent_potential_actions_fainted_pokemon_excluded(self) -> None:
        """Test that fainted Pokemon are not included in switch options."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard", current_hp=80, max_hp=100, is_active=True
        )
        opponent_blastoise = PokemonState(species="Blastoise", current_hp=0, max_hp=100)
        opponent_venusaur = PokemonState(
            species="Venusaur", current_hp=50, max_hp=100
        )
        opponent_team = TeamState(
            pokemon=[opponent_charizard, opponent_blastoise, opponent_venusaur],
            active_pokemon_index=0,
        )

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        actions = state.get_opponent_potential_actions()

        switch_actions = [a for a in actions if a.action_type == ActionType.SWITCH]

        self.assertEqual(len(switch_actions), 1)
        self.assertEqual(switch_actions[0].switch_pokemon_name, "Venusaur")

    def test_opponent_potential_actions_no_our_player_id_requires_param(self) -> None:
        """Test that player parameter is required when our_player_id is not set."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard", current_hp=80, max_hp=100, is_active=True
        )
        opponent_team = TeamState(pokemon=[opponent_charizard], active_pokemon_index=0)

        state = BattleState(teams={"p1": our_team, "p2": opponent_team})

        with self.assertRaises(ValueError) as cm:
            state.get_opponent_potential_actions()

        self.assertIn("our_player_id is not set", str(cm.exception))

    def test_opponent_potential_actions_with_explicit_player(self) -> None:
        """Test opponent actions work with explicit player parameter."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard",
            current_hp=80,
            max_hp=100,
            moves=[PokemonMove(name="Flamethrower", current_pp=15, max_pp=15)],
            is_active=True,
        )
        opponent_team = TeamState(pokemon=[opponent_charizard], active_pokemon_index=0)

        state = BattleState(teams={"p1": our_team, "p2": opponent_team})

        actions = state.get_opponent_potential_actions(player="p2")

        move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
        self.assertEqual(len(move_actions), 1)
        self.assertEqual(move_actions[0].move_name, "Flamethrower")

    def test_opponent_potential_actions_error_if_our_own_player(self) -> None:
        """Test error when trying to get opponent actions for our own player."""
        our_pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        our_team = TeamState(pokemon=[our_pikachu], active_pokemon_index=0)

        opponent_charizard = PokemonState(
            species="Charizard", current_hp=80, max_hp=100, is_active=True
        )
        opponent_team = TeamState(pokemon=[opponent_charizard], active_pokemon_index=0)

        state = BattleState(
            teams={"p1": our_team, "p2": opponent_team}, our_player_id="p1"
        )

        with self.assertRaises(ValueError) as cm:
            state.get_opponent_potential_actions(player="p1")

        self.assertIn("Cannot get opponent actions for our own player", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
