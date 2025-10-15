"""Battle simulation tools for calculating Pokemon stats and simulating scenarios."""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from python.game.data.game_data import GameData
from python.game.schema.enums import SideCondition, Stat, Status, Terrain, Weather
from python.game.schema.field_state import FieldState
from python.game.schema.object_name_normalizer import normalize_name
from python.game.schema.pokemon_state import (
    STAT_STAGE_MULTIPLIERS,
    PokemonMove,
    PokemonState,
)


@dataclass(frozen=True)
class IndividualValues:
    """Individual Values (IVs) for a Pokemon, ranging from 0-31."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def __post_init__(self) -> None:
        for field_name in [
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0 or value > 31:
                raise ValueError(
                    f"{field_name} IV must be between 0 and 31, got {value}"
                )


@dataclass(frozen=True)
class EffortValues:
    """Effort Values (EVs) for a Pokemon, ranging from 0-252."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def __post_init__(self) -> None:
        for field_name in [
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0 or value > 252:
                raise ValueError(
                    f"{field_name} EV must be between 0 and 252, got {value}"
                )


@dataclass(frozen=True)
class PokemonStats:
    """Calculated stats for a Pokemon."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int


@dataclass(frozen=True)
class MoveAction:
    """Represents a move action with its priority and speed."""

    pokemon: PokemonState
    move: PokemonMove
    priority: int
    fractional_priority: float
    speed: int


@dataclass(frozen=True)
class MoveResult:
    """Result of estimating a move's damage and effects."""

    min_damage: int
    max_damage: int
    knockout_probability: float
    critical_hit_probability: float
    status_effects: Dict[str, float]
    additional_effects: List[str]


class BattleSimulator:
    """Simulator for calculating Pokemon stats and battle scenarios."""

    def __init__(self, game_data: GameData) -> None:
        """Initialize the battle simulator.

        Args:
            game_data: GameData instance for looking up Pokemon, natures, etc.
        """
        self.game_data = game_data

    def get_nature_boosts(self, nature: str) -> Dict[str, float]:
        nature_data = self.game_data.get_nature(nature)

        stat_name_map = {
            "atk": "attack",
            "def": "defense",
            "spa": "special_attack",
            "spd": "special_defense",
            "spe": "speed",
        }

        multipliers = {
            "hp": 1.0,
            "attack": 1.0,
            "defense": 1.0,
            "special_attack": 1.0,
            "special_defense": 1.0,
            "speed": 1.0,
        }

        if nature_data.plus_stat:
            full_stat_name = stat_name_map.get(
                nature_data.plus_stat, nature_data.plus_stat
            )
            multipliers[full_stat_name] = 1.1

        if nature_data.minus_stat:
            full_stat_name = stat_name_map.get(
                nature_data.minus_stat, nature_data.minus_stat
            )
            multipliers[full_stat_name] = 0.9

        return multipliers

    def get_pokemon_stats(
        self,
        pokemon: PokemonState,
        level: int = 100,
        ivs: IndividualValues = IndividualValues(31, 31, 31, 31, 31, 31),
        evs: EffortValues = EffortValues(252, 252, 252, 252, 252, 252),
        nature: str = "Bashful",
    ) -> PokemonStats:
        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        base_stats = pokemon_data.base_stats
        nature_multipliers = self.get_nature_boosts(nature)

        hp = int(
            int(2 * base_stats["hp"] + ivs.hp + int(evs.hp / 4) + 100) * level / 100
            + 10
        )

        attack = int(
            int(
                int(2 * base_stats["atk"] + ivs.attack + int(evs.attack / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["attack"]
        )

        defense = int(
            int(
                int(2 * base_stats["def"] + ivs.defense + int(evs.defense / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["defense"]
        )

        special_attack = int(
            int(
                int(
                    2 * base_stats["spa"]
                    + ivs.special_attack
                    + int(evs.special_attack / 4)
                )
                * level
                / 100
                + 5
            )
            * nature_multipliers["special_attack"]
        )

        special_defense = int(
            int(
                int(
                    2 * base_stats["spd"]
                    + ivs.special_defense
                    + int(evs.special_defense / 4)
                )
                * level
                / 100
                + 5
            )
            * nature_multipliers["special_defense"]
        )

        speed = int(
            int(
                int(2 * base_stats["spe"] + ivs.speed + int(evs.speed / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["speed"]
        )

        return PokemonStats(
            hp=hp,
            attack=attack,
            defense=defense,
            special_attack=special_attack,
            special_defense=special_defense,
            speed=speed,
        )

    def calculate_move_priority(
        self, pokemon: PokemonState, move: PokemonMove
    ) -> Tuple[int, float]:
        move_data = self.game_data.get_move(move.name)
        base_priority = move_data.priority
        fractional_priority = 0.0

        ability = normalize_name(pokemon.ability) if pokemon.ability else ""
        item = normalize_name(pokemon.item) if pokemon.item else ""

        if ability == "prankster" and move_data.category == "Status":
            base_priority += 1

        if ability == "galewings" and move_data.type == "Flying":
            if pokemon.current_hp == pokemon.max_hp:
                base_priority += 1

        if ability == "triage":
            move_flags = self._get_move_flags(move.name)
            if "heal" in move_flags:
                base_priority += 3

        if item == "quickclaw":
            if random.random() < 0.2:
                fractional_priority = 0.1

        if item in ["laggingtail", "fullincense"]:
            fractional_priority = -0.1

        return base_priority, fractional_priority

    def _get_move_flags(self, move_name: str) -> List[str]:
        healing_moves = {
            "Absorb",
            "Draining Kiss",
            "Drain Punch",
            "Giga Drain",
            "Horn Leech",
            "Leech Life",
            "Mega Drain",
            "Parabolic Charge",
            "Dream Eater",
        }
        if move_name in healing_moves:
            return ["heal"]
        return []

    def calculate_action_speed(
        self,
        pokemon: PokemonState,
        base_speed: int,
        weather: Weather = Weather.NONE,
        terrain: Optional[Terrain] = None,
        side_conditions: Optional[set] = None,
        trick_room_active: bool = False,
    ) -> int:
        speed_stat = self.get_pokemon_stats(pokemon).speed
        boost_multiplier = STAT_STAGE_MULTIPLIERS.get(
            pokemon.get_stat_boost(Stat.SPE), 1.0
        )
        speed = speed_stat * boost_multiplier

        ability = normalize_name(pokemon.ability) if pokemon.ability else ""
        item = normalize_name(pokemon.item) if pokemon.item else ""

        if ability == "swiftswim" and weather in [
            Weather.RAIN,
            Weather.HEAVY_RAIN,
        ]:
            speed *= 2
        if ability == "chlorophyll" and weather in [
            Weather.SUN,
            Weather.HARSH_SUN,
        ]:
            speed *= 2
        if ability == "sandrush" and weather == Weather.SANDSTORM:
            speed *= 2
        if ability == "slushrush" and weather == Weather.SNOW:
            speed *= 2
        if ability == "surgesurfer" and terrain == Terrain.ELECTRIC:
            speed *= 2
        if item == "choicescarf":
            speed *= 1.5

        if item in [
            "ironball",
            "machobrace",
            "powerbracer",
            "powerbelt",
            "powerlens",
            "powerband",
            "poweranklet",
            "powerweight",
        ]:
            speed *= 0.5

        if side_conditions and SideCondition.TAILWIND in side_conditions:
            speed *= 2

        if pokemon.status == Status.PARALYSIS:
            speed = int(speed)
            speed = int(speed * 0.5)
        else:
            speed = int(speed)

        if trick_room_active:
            speed = 10000 - speed

        return speed

    def get_move_order(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        side_1_conditions: Optional[set] = None,
        side_2_conditions: Optional[set] = None,
        weather: Weather = Weather.NONE,
        terrain: Optional[Terrain] = None,
        trick_room_active: bool = False,
    ) -> List[MoveAction]:
        pokemon_1_data = self.game_data.get_pokemon(pokemon_1.species)
        pokemon_2_data = self.game_data.get_pokemon(pokemon_2.species)

        base_speed_1 = pokemon_1_data.base_stats["spe"]
        base_speed_2 = pokemon_2_data.base_stats["spe"]

        priority_1, frac_priority_1 = self.calculate_move_priority(pokemon_1, move_1)
        priority_2, frac_priority_2 = self.calculate_move_priority(pokemon_2, move_2)

        speed_1 = self.calculate_action_speed(
            pokemon_1,
            base_speed_1,
            weather,
            terrain,
            side_1_conditions,
            trick_room_active,
        )
        speed_2 = self.calculate_action_speed(
            pokemon_2,
            base_speed_2,
            weather,
            terrain,
            side_2_conditions,
            trick_room_active,
        )

        action_1 = MoveAction(
            pokemon=pokemon_1,
            move=move_1,
            priority=priority_1,
            fractional_priority=frac_priority_1,
            speed=speed_1,
        )
        action_2 = MoveAction(
            pokemon=pokemon_2,
            move=move_2,
            priority=priority_2,
            fractional_priority=frac_priority_2,
            speed=speed_2,
        )

        if priority_1 != priority_2:
            return (
                [action_1, action_2]
                if priority_1 > priority_2
                else [action_2, action_1]
            )

        total_priority_1 = priority_1 + frac_priority_1
        total_priority_2 = priority_2 + frac_priority_2
        if total_priority_1 != total_priority_2:
            return (
                [action_1, action_2]
                if total_priority_1 > total_priority_2
                else [action_2, action_1]
            )

        if speed_1 != speed_2:
            return [action_1, action_2] if speed_1 > speed_2 else [action_2, action_1]

        return [action_1, action_2] if random.random() < 0.5 else [action_2, action_1]

    def estimate_move_result(
        self,
        attacking_pokemon: PokemonState,
        target_pokemon: PokemonState,
        move: PokemonMove,
        field_state: Optional[FieldState] = None,
        defender_side_conditions: Optional[List[SideCondition]] = None,
    ) -> MoveResult:
        move_data = self.game_data.get_move(move.name)

        if move_data.category == "Status":
            return MoveResult(
                min_damage=0,
                max_damage=0,
                knockout_probability=0.0,
                critical_hit_probability=0.0,
                status_effects={},
                additional_effects=[],
            )

        attacker_stats = self.get_pokemon_stats(
            attacking_pokemon, attacking_pokemon.level
        )
        defender_stats = self.get_pokemon_stats(target_pokemon, target_pokemon.level)

        if move_data.override_offensive_stat:
            if move_data.override_offensive_stat == "def":
                attack_stat = Stat.DEF
                attacker_stat_value = attacker_stats.defense
            elif move_data.override_offensive_stat == "spd":
                attack_stat = Stat.SPD
                attacker_stat_value = attacker_stats.special_defense
            else:
                if move_data.category == "Physical":
                    attack_stat = Stat.ATK
                    attacker_stat_value = attacker_stats.attack
                else:
                    attack_stat = Stat.SPA
                    attacker_stat_value = attacker_stats.special_attack
        elif move_data.category == "Physical":
            attack_stat = Stat.ATK
            attacker_stat_value = attacker_stats.attack
        else:
            attack_stat = Stat.SPA
            attacker_stat_value = attacker_stats.special_attack

        if move_data.override_defensive_stat:
            if move_data.override_defensive_stat == "def":
                defense_stat = Stat.DEF
                defender_stat_value = defender_stats.defense
            elif move_data.override_defensive_stat == "spd":
                defense_stat = Stat.SPD
                defender_stat_value = defender_stats.special_defense
            else:
                if move_data.category == "Physical":
                    defense_stat = Stat.DEF
                    defender_stat_value = defender_stats.defense
                else:
                    defense_stat = Stat.SPD
                    defender_stat_value = defender_stats.special_defense
        elif move_data.category == "Physical":
            defense_stat = Stat.DEF
            defender_stat_value = defender_stats.defense
        else:
            defense_stat = Stat.SPD
            defender_stat_value = defender_stats.special_defense

        attack_multiplier = attacking_pokemon.get_stat_multiplier(attack_stat)
        defense_multiplier = target_pokemon.get_stat_multiplier(defense_stat)

        attack = int(attacker_stat_value * attack_multiplier)
        defense = int(defender_stat_value * defense_multiplier)

        level = attacking_pokemon.level
        base_power = move_data.base_power

        base_damage = (
            int(int(int(int(2 * level / 5 + 2) * base_power * attack) / defense) / 50)
            + 2
        )

        crit_ratio = 0
        if crit_ratio == 0:
            crit_chance = 1 / 24
        elif crit_ratio == 1:
            crit_chance = 1 / 8
        elif crit_ratio == 2:
            crit_chance = 1 / 2
        else:
            crit_chance = 1.0

        damage = self._apply_modifiers(
            base_damage,
            attacking_pokemon,
            target_pokemon,
            move_data,
            field_state,
            defender_side_conditions,
            is_crit=False,
        )

        min_damage = int(damage * 0.85)
        max_damage = int(damage * 1.0)

        ko_prob = 0.0
        if min_damage >= target_pokemon.current_hp:
            ko_prob = 1.0
        elif max_damage >= target_pokemon.current_hp:
            ko_prob = 0.5

        status_effects: Dict[str, float] = {}
        additional_effects: List[str] = []

        return MoveResult(
            min_damage=min_damage,
            max_damage=max_damage,
            knockout_probability=ko_prob,
            critical_hit_probability=crit_chance,
            status_effects=status_effects,
            additional_effects=additional_effects,
        )

    def _is_grounded(self, pokemon: PokemonState) -> bool:
        ability = normalize_name(pokemon.ability) if pokemon.ability else ""
        if ability == "levitate":
            return False

        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        types = pokemon_data.types
        if "Flying" in types:
            return False

        return True

    def _apply_modifiers(
        self,
        base_damage: int,
        attacker: PokemonState,
        defender: PokemonState,
        move_data,
        field_state: Optional[FieldState],
        defender_side_conditions: Optional[List[SideCondition]],
        is_crit: bool,
    ) -> float:
        damage = float(base_damage)

        weather = field_state.get_weather() if field_state else None
        if weather == Weather.RAIN:
            if move_data.type == "Water":
                damage *= 1.5
            elif move_data.type == "Fire":
                damage *= 0.5
        elif weather == Weather.SUN:
            if move_data.type == "Fire":
                damage *= 1.5
            elif move_data.type == "Water":
                damage *= 0.5

        if is_crit:
            damage *= 1.5

        terrain = field_state.get_terrain() if field_state else None
        if terrain and self._is_grounded(attacker):
            if terrain == Terrain.ELECTRIC and move_data.type == "Electric":
                damage *= 1.3
            elif terrain == Terrain.GRASSY and move_data.type == "Grass":
                damage *= 1.3
            elif terrain == Terrain.PSYCHIC and move_data.type == "Psychic":
                damage *= 1.3
            elif terrain == Terrain.MISTY and move_data.type == "Dragon":
                damage *= 0.5

        attacker_pokemon_data = self.game_data.get_pokemon(attacker.species)
        attacker_types = attacker_pokemon_data.types
        if attacker.has_terastallized and attacker.tera_type:
            attacker_types = [attacker.tera_type]

        is_stab = move_data.type in attacker_types
        if is_stab:
            if attacker.has_terastallized:
                damage *= 2.0
            else:
                damage *= 1.5

        defender_pokemon_data = self.game_data.get_pokemon(defender.species)
        defender_types = defender_pokemon_data.types
        if defender.has_terastallized and defender.tera_type:
            defender_types = [defender.tera_type]

        type_effectiveness = 1.0
        type_chart = self.game_data.get_type_chart()
        for defender_type in defender_types:
            effectiveness = type_chart.get_effectiveness(move_data.type, defender_type)
            type_effectiveness *= effectiveness

        damage *= type_effectiveness

        if attacker.status == Status.BURN and move_data.category == "Physical":
            damage *= 0.5

        if defender_side_conditions:
            if SideCondition.AURORA_VEIL in defender_side_conditions:
                damage *= 0.5
            elif (
                move_data.category == "Physical"
                and SideCondition.REFLECT in defender_side_conditions
            ):
                damage *= 0.5
            elif (
                move_data.category == "Special"
                and SideCondition.LIGHT_SCREEN in defender_side_conditions
            ):
                damage *= 0.5

        return damage
