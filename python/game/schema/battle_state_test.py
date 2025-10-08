"""Integration tests for BattleState based on real battle logs."""

import json
import unittest

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
        p1_pokemon = [
            PokemonState(species="Iron Crown", current_hp=94, max_hp=100)
        ]
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
            p1_team=p1_team,
            p2_team=p2_team,
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
        p1_pokemon = [
            PokemonState(species="Iron Crown", current_hp=58, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        p2_pokemon = [
            PokemonState(species="Gholdengo", current_hp=50, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.STEALTH_ROCK: 1},
        )

        field = FieldState(turn_number=10)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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
            p1_team=p1_team,
            p2_team=p2_team,
            field_state=field,
        )

        raging_bolt = battle.get_active_pokemon("p1")
        self.assertIsNotNone(raging_bolt)
        stats = battle.get_pokemon_battle_state(raging_bolt)  # type: ignore
        self.assertEqual(stats["status"], "brn")
        self.assertEqual(stats["hp"]["current"], 56)

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

        p1_pokemon = [
            PokemonState(species="Zamazenta", current_hp=37, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=24)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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

        p2_pokemon = [
            PokemonState(species="Glimmora", current_hp=73, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=3)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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
        p1_pokemon = [
            PokemonState(species="Deoxys", current_hp=11, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={
                SideCondition.LIGHT_SCREEN: 5,
                SideCondition.REFLECT: 5,
            },
        )

        p2_pokemon = [
            PokemonState(species="Darkrai", current_hp=100, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=4)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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

        p1_pokemon = [
            PokemonState(species="Dondozo", current_hp=56, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=37)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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

        p1_pokemon = [
            PokemonState(species="Dondozo", current_hp=72, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(
            weather=Weather.SNOW, weather_turns_remaining=5, turn_number=16
        )

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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

        p1_pokemon = [
            PokemonState(species="Toxapex", current_hp=28, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=22)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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
        p1_pokemon = [
            PokemonState(species="Ribombee", current_hp=100, max_hp=100)
        ]
        p1_team = TeamState(
            player_id="p1",
            pokemon=p1_pokemon,
            active_pokemon_index=0,
            side_conditions={SideCondition.TAILWIND: 4},
        )

        p2_pokemon = [
            PokemonState(species="Kingambit", current_hp=100, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=10)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
            field_state=field,
        )

        field_info = battle.get_field_info()
        self.assertEqual(field_info["p1_side_conditions"]["tailwind"], 4)

    def test_trick_room(self) -> None:
        """Test Case 11: Line 23544 - Trick Room field effect."""
        p2_pokemon = [
            PokemonState(species="Hatterene", current_hp=100, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        p1_pokemon = [
            PokemonState(species="Cinderace", current_hp=80, max_hp=100)
        ]
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
            p1_team=p1_team,
            p2_team=p2_team,
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

        p2_pokemon = [
            PokemonState(species="Kingambit", current_hp=81, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=27)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
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
        state = BattleState(p1_team=team, p2_team=TeamState())

        # Get available moves - should exclude Thunder Wave (no PP)
        moves = state.get_available_moves("p1")
        self.assertEqual(set(moves), {"Thunderbolt", "Volt Switch"})

    def test_infer_available_switches(self) -> None:
        """Test switch inference from battle state."""
        pikachu = PokemonState(
            species="Pikachu", current_hp=100, max_hp=100, is_active=True
        )
        charizard = PokemonState(species="Charizard", current_hp=80, max_hp=100)
        fainted = PokemonState(species="Blastoise", current_hp=0, max_hp=100)

        team = TeamState(pokemon=[pikachu, charizard, fainted], active_pokemon_index=0)
        state = BattleState(p1_team=team, p2_team=TeamState())

        switches = state.get_available_switches("p1")
        self.assertEqual(switches, [1])

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
        state = BattleState(p1_team=team, p2_team=TeamState())

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
        state = BattleState(p1_team=team, p2_team=TeamState())

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
        state = BattleState(p1_team=team, p2_team=TeamState())

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
        state = BattleState(p1_team=team, p2_team=TeamState())

        # All moves except Thunderbolt should be available
        moves = state.get_available_moves("p1")
        self.assertEqual(
            set(moves), {"Volt Switch", "Quick Attack", "Thunder Wave"}
        )

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
        state = BattleState(p1_team=team, p2_team=TeamState())

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
        state = BattleState(p1_team=team, p2_team=TeamState())

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

        p2_pokemon = [
            PokemonState(species="Kommo-o", current_hp=100, max_hp=100)
        ]
        p2_team = TeamState(
            player_id="p2",
            pokemon=p2_pokemon,
            active_pokemon_index=0,
        )

        field = FieldState(turn_number=1)

        battle = BattleState(
            p1_team=p1_team,
            p2_team=p2_team,
            field_state=field,
            battle_format="singles",
        )

        json_str = str(battle)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["battle_format"], "singles")
        self.assertEqual(parsed["field_state"]["turn_number"], 1)
        self.assertIn("stealthrock", parsed["p1_team"]["side_conditions"])


if __name__ == "__main__":
    unittest.main()
