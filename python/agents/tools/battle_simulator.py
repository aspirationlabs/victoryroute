"""Battle simulation tools for calculating Pokemon stats and simulating scenarios."""

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

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
    crit_min_damage: int
    crit_max_damage: int
    status_effects: Dict[str, float]
    additional_effects: List[str]
    hit_count: Union[int, str] = 1
    recoil_damage: int = 0
    drain_heal: int = 0
    status_infliction_chances: Dict[str, float] = field(default_factory=dict)
    stat_change_chances: Dict[str, Tuple[Stat, int, float]] = field(
        default_factory=dict
    )


class BattleSimulator:
    """Simulator for calculating Pokemon stats and battle scenarios."""

    TYPE_BOOST_ITEMS: Dict[str, str] = {
        "blackbelt": "Fighting",
        "fistplate": "Fighting",
        "charcoal": "Fire",
        "flameplate": "Fire",
        "mysticwater": "Water",
        "splashplate": "Water",
        "seaincense": "Water",
        "waveincense": "Water",
        "magnet": "Electric",
        "zapplate": "Electric",
        "miracleseed": "Grass",
        "meadowplate": "Grass",
        "roseincense": "Grass",
        "nevermeltice": "Ice",
        "icicleplate": "Ice",
        "blackglasses": "Dark",
        "dreadplate": "Dark",
        "poisonbarb": "Poison",
        "toxicplate": "Poison",
        "softsand": "Ground",
        "earthplate": "Ground",
        "sharpebeak": "Flying",
        "skyplate": "Flying",
        "twistedspoon": "Psychic",
        "oddincense": "Psychic",
        "mindplate": "Psychic",
        "silverpowder": "Bug",
        "insectplate": "Bug",
        "hardstone": "Rock",
        "stoneplate": "Rock",
        "rockincense": "Rock",
        "spelltag": "Ghost",
        "spookyplate": "Ghost",
        "dragonfang": "Dragon",
        "dracoplate": "Dragon",
        "metalcoat": "Steel",
        "ironplate": "Steel",
        "silkscarf": "Normal",
        "pinkbow": "Normal",
        "polkadotbow": "Normal",
        "pixieplate": "Fairy",
        "fairyfeather": "Fairy",
    }

    SPECIES_TYPE_BOOST_ITEMS: Dict[str, Dict[str, Any]] = {
        "adamantorb": {
            "species": {"dialga", "dialgaorigin"},
            "types": {"Steel", "Dragon"},
            "multiplier": 1.2,
        },
        "adamantcrystal": {
            "species": {"dialga", "dialgaorigin"},
            "types": {"Steel", "Dragon"},
            "multiplier": 1.2,
        },
        "lustrousorb": {
            "species": {"palkia", "palkiaorigin"},
            "types": {"Water", "Dragon"},
            "multiplier": 1.2,
        },
        "lustrousglobe": {
            "species": {"palkia", "palkiaorigin"},
            "types": {"Water", "Dragon"},
            "multiplier": 1.2,
        },
        "griseousorb": {
            "species": {"giratina", "giratinaorigin"},
            "types": {"Ghost", "Dragon"},
            "multiplier": 1.2,
        },
        "griseouscore": {
            "species": {"giratina", "giratinaorigin"},
            "types": {"Ghost", "Dragon"},
            "multiplier": 1.2,
        },
        "souldew": {
            "species": {
                "latias",
                "latiasmega",
                "latios",
                "latiosmega",
            },
            "types": {"Dragon", "Psychic"},
            "multiplier": 1.2,
        },
        "vilevial": {
            "species": {"venomicon", "venomiconepilogue"},
            "types": {"Poison", "Flying"},
            "multiplier": 1.2,
        },
        "cornerstonemask": {
            "species": {
                "ogerponcornerstone",
                "ogerponcornerstonetera",
            },
            "types": None,
            "multiplier": 1.2,
        },
        "wellspringmask": {
            "species": {
                "ogerponwellspring",
                "ogerponwellspringtera",
            },
            "types": None,
            "multiplier": 1.2,
        },
        "hearthflamemask": {
            "species": {
                "ogerponhearthflame",
                "ogerponhearthflametera",
            },
            "types": None,
            "multiplier": 1.2,
        },
    }

    BASE_POWER_CALLBACK_TYPES: Dict[str, str] = {
        "eruption": "hp_based_attacker",
        "waterspout": "hp_based_attacker",
        "crushgrip": "hp_based_defender",
        "wringout": "hp_based_defender",
        "electroball": "speed_ratio",
        "gyroball": "inverse_speed_ratio",
        "heavyslam": "weight_ratio",
        "heatcrash": "weight_ratio",
        "lowkick": "target_weight",
        "grassknot": "target_weight",
        "storedpower": "positive_boosts",
        "powertrip": "positive_boosts",
    }

    RECOIL_MOVE_DATA: Dict[str, Tuple[int, int]] = {
        "doubleedge": (33, 100),
        "bravebird": (33, 100),
        "flareblitz": (33, 100),
        "headsmash": (1, 2),
        "wavecrash": (33, 100),
    }

    DRAIN_MOVE_DATA: Dict[str, Tuple[int, int]] = {
        "gigadrain": (1, 2),
        "drainpunch": (1, 2),
        "drainingkiss": (3, 4),
        "paraboliccharge": (3, 4),
    }

    SECONDARY_EFFECTS_DATA: Dict[str, List[Dict[str, Any]]] = {
        "thunderbolt": [{"chance": 10, "status": "par"}],
        "flamethrower": [{"chance": 10, "status": "brn"}],
        "scald": [{"chance": 30, "status": "brn"}],
        "shadowball": [{"chance": 20, "boosts": {"spd": -1}}],
        "crunch": [{"chance": 20, "boosts": {"def": -1}}],
    }

    MOVE_FLAGS_DATA: Dict[str, List[str]] = {
        "machpunch": ["contact", "protect", "mirror", "punch", "metronome"],
        "crunch": ["contact", "protect", "mirror", "metronome", "bite"],
        "aurasphere": ["protect", "mirror", "distance", "metronome", "bullet", "pulse"],
        "aquacutter": ["protect", "mirror", "metronome", "slicing"],
    }

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

    def _get_base_power_callback_type(self, move_data, move_name: str) -> Optional[str]:
        if move_data.base_power_callback_type:
            return move_data.base_power_callback_type
        return self.BASE_POWER_CALLBACK_TYPES.get(normalize_name(move_name))

    def _get_pokemon_weight_hg(self, pokemon: PokemonState) -> int:
        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        if pokemon_data.weight_kg is None:
            return 0
        weight_hg = int(pokemon_data.weight_kg * 10)
        return max(weight_hg, 0)

    def _get_effective_speed(
        self,
        pokemon: PokemonState,
        field_state: Optional[FieldState],
        side_conditions: Optional[List[SideCondition]] = None,
    ) -> int:
        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        base_speed = pokemon_data.base_stats["spe"]

        weather = field_state.get_weather() if field_state else None
        terrain = field_state.get_terrain() if field_state else None

        side_condition_set = set(side_conditions) if side_conditions else None

        effective_speed = self.calculate_action_speed(
            pokemon,
            base_speed,
            weather or Weather.NONE,
            terrain,
            side_condition_set,
            trick_room_active=False,
        )
        return max(1, effective_speed)

    def _calculate_effective_base_power(
        self,
        move: PokemonMove,
        move_data,
        attacker: PokemonState,
        defender: PokemonState,
        field_state: Optional[FieldState],
        defender_side_conditions: Optional[List[SideCondition]],
    ) -> int:
        callback_type = self._get_base_power_callback_type(move_data, move.name)
        base_power = move_data.base_power

        if not callback_type:
            return base_power

        if callback_type == "hp_based_attacker":
            if attacker.max_hp <= 0:
                return base_power
            scaled = base_power * attacker.current_hp / attacker.max_hp
            return max(1, int(scaled))

        if callback_type == "hp_based_defender":
            if defender.max_hp <= 0:
                return 1
            hp = defender.current_hp
            max_hp = defender.max_hp
            scaled_hp = math.floor(hp * 4096 / max_hp)
            numerator = 120 * (100 * scaled_hp)
            interim = math.floor((numerator + 2048 - 1) / 4096)
            bp = math.floor(interim / 100)
            return max(1, bp)

        if callback_type == "speed_ratio":
            attacker_speed = self._get_effective_speed(attacker, field_state)
            defender_speed = self._get_effective_speed(
                defender, field_state, defender_side_conditions
            )
            ratio = 0
            if defender_speed > 0:
                ratio = math.floor(attacker_speed / defender_speed)
            ratio = max(0, min(4, ratio))
            return [40, 60, 80, 120, 150][ratio]

        if callback_type == "inverse_speed_ratio":
            attacker_speed = self._get_effective_speed(attacker, field_state)
            defender_speed = self._get_effective_speed(
                defender, field_state, defender_side_conditions
            )
            if attacker_speed <= 0:
                attacker_speed = 1
            bp = math.floor(25 * defender_speed / attacker_speed) + 1
            return max(1, min(150, bp))

        if callback_type == "weight_ratio":
            attacker_weight = self._get_pokemon_weight_hg(attacker)
            defender_weight = self._get_pokemon_weight_hg(defender)
            if defender_weight <= 0:
                return 120
            ratio = attacker_weight / defender_weight
            if ratio >= 5:
                return 120
            if ratio >= 4:
                return 100
            if ratio >= 3:
                return 80
            if ratio >= 2:
                return 60
            return 40

        if callback_type == "target_weight":
            target_weight = self._get_pokemon_weight_hg(defender)
            if target_weight >= 2000:
                return 120
            if target_weight >= 1000:
                return 100
            if target_weight >= 500:
                return 80
            if target_weight >= 250:
                return 60
            if target_weight >= 100:
                return 40
            return 20

        if callback_type == "positive_boosts":
            positive_boosts = 0
            for boost in attacker.stat_boosts.values():
                if boost > 0:
                    positive_boosts += boost
            return max(1, 20 + 20 * positive_boosts)

        return base_power

    def _get_move_recoil(self, move_data, move_name: str) -> Optional[Tuple[int, int]]:
        if move_data.recoil:
            recoil_tuple = tuple(move_data.recoil)
            return recoil_tuple if recoil_tuple else None
        return self.RECOIL_MOVE_DATA.get(normalize_name(move_name))

    def _get_move_drain(self, move_data, move_name: str) -> Optional[Tuple[int, int]]:
        if move_data.drain:
            drain_tuple = tuple(move_data.drain)
            return drain_tuple if drain_tuple else None
        return self.DRAIN_MOVE_DATA.get(normalize_name(move_name))

    def _round_half_up(self, value: float) -> int:
        if value <= 0:
            return 0
        return int(math.floor(value + 0.5))

    def _calculate_recoil_damage(
        self,
        recoil: Optional[Tuple[int, int]],
        damage: int,
        attacker: PokemonState,
    ) -> int:
        if not recoil or damage <= 0:
            return 0
        ability = self._get_ability(attacker)
        if ability in {"rockhead", "magicguard"}:
            return 0
        numerator, denominator = recoil
        recoil_damage = self._round_half_up(damage * numerator / denominator)
        if recoil_damage == 0 and damage > 0:
            return 1
        return recoil_damage

    def _calculate_drain_heal(
        self,
        drain: Optional[Tuple[int, int]],
        damage: int,
        attacker: PokemonState,
        defender: PokemonState,
    ) -> int:
        if not drain or damage <= 0:
            return 0
        numerator, denominator = drain
        heal_amount = self._round_half_up(damage * numerator / denominator)
        if heal_amount == 0 and damage > 0:
            heal_amount = 1
        defender_ability = self._get_ability(defender)
        if defender_ability == "liquidooze":
            return -heal_amount
        return heal_amount

    def _get_secondary_effects(self, move_data, move_name: str) -> List[Dict[str, Any]]:
        effects: List[Dict[str, Any]] = []
        if move_data.secondary_effects:
            effects.extend(dict(effect) for effect in move_data.secondary_effects)
        if not effects:
            fallback = self.SECONDARY_EFFECTS_DATA.get(normalize_name(move_name))
            if fallback:
                effects.extend(dict(effect) for effect in fallback)
        return effects

    def _move_has_target_secondary_effect(
        self, secondary_effects: List[Dict[str, Any]]
    ) -> bool:
        for effect in secondary_effects:
            if (
                effect.get("status")
                or effect.get("boosts")
                or effect.get("volatile_status")
            ):
                return True
        return False

    def _stat_from_key(self, stat_key: str) -> Optional[Stat]:
        key_upper = stat_key.upper()
        try:
            return Stat[key_upper]
        except KeyError:
            for stat in Stat:
                if stat.value == stat_key.lower():
                    return stat
        return None

    def _status_from_string(self, status_key: str) -> Optional[Status]:
        for status in Status:
            if status.value == status_key:
                return status
        return None

    def _calculate_secondary_effects(
        self,
        secondary_effects: List[Dict[str, Any]],
        attacker_ability: str,
        defender_ability: str,
    ) -> Tuple[Dict[str, float], Dict[str, Tuple[Stat, int, float]], List[str]]:
        if not secondary_effects:
            return {}, {}, []

        if attacker_ability == "sheerforce":
            return {}, {}, []

        if defender_ability == "shielddust":
            return {}, {}, []

        serene_grace = attacker_ability == "serenegrace"

        status_chances: Dict[str, float] = {}
        stat_chances: Dict[str, Tuple[Stat, int, float]] = {}
        additional_effects: List[str] = []

        for effect in secondary_effects:
            chance = float(effect.get("chance", 100))
            if serene_grace:
                chance = min(100.0, chance * 2)
            chance = max(0.0, min(100.0, chance))
            probability = chance / 100.0
            if probability <= 0:
                continue

            status_key = effect.get("status")
            if status_key:
                status_enum = self._status_from_string(status_key)
                key = status_enum.value if status_enum else status_key
                status_chances[key] = probability

            boosts = effect.get("boosts")
            if boosts:
                for stat_key, change in boosts.items():
                    stat_enum = self._stat_from_key(stat_key)
                    if not stat_enum:
                        continue
                    stat_chances[stat_enum.value] = (
                        stat_enum,
                        int(change),
                        probability,
                    )

            volatile_status = effect.get("volatile_status")
            if volatile_status:
                additional_effects.append(f"{volatile_status}:{probability:.2f}")

        return status_chances, stat_chances, additional_effects

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
                crit_min_damage=0,
                crit_max_damage=0,
                status_effects={},
                additional_effects=[],
            )

        secondary_effects = self._get_secondary_effects(move_data, move.name)
        has_target_secondary_effect = self._move_has_target_secondary_effect(
            secondary_effects
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

        attacker_ability = self._get_ability(attacking_pokemon)
        defender_ability = self._get_ability(target_pokemon)

        ignores_defender_ability = attacker_ability in {
            "moldbreaker",
            "teravolt",
            "turboblaze",
        }

        attack_multiplier = attacking_pokemon.get_stat_multiplier(attack_stat)
        defense_multiplier = target_pokemon.get_stat_multiplier(defense_stat)

        weather = field_state.get_weather() if field_state else None
        weather_defense_modifier = self._get_weather_stat_modifier(
            target_pokemon, defense_stat, weather
        )

        attack = int(attacker_stat_value * attack_multiplier)
        defense = int(
            defender_stat_value * defense_multiplier * weather_defense_modifier
        )

        weather = field_state.get_weather() if field_state else None

        attack = self._modify_attack_for_ability(
            attack,
            attack_stat,
            attacker_ability,
            move_data,
            attacking_pokemon,
            weather,
        )
        defense = self._modify_defense_for_ability(
            defense,
            defense_stat,
            defender_ability,
            target_pokemon,
            ignores_defender_ability,
        )

        level = attacking_pokemon.level
        base_power = self._calculate_effective_base_power(
            move,
            move_data,
            attacking_pokemon,
            target_pokemon,
            field_state,
            defender_side_conditions,
        )

        if attacker_ability == "technician" and base_power <= 60:
            base_power = int(base_power * 1.5)

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
            attacker_ability=attacker_ability,
            defender_ability=defender_ability,
            has_target_secondary_effect=has_target_secondary_effect,
        )

        min_damage = int(damage * 0.85)
        max_damage = int(damage * 1.0)

        crit_attack_multiplier = self._get_crit_stat_multiplier(
            attacking_pokemon, attack_stat, is_attacker=True
        )
        crit_defense_multiplier = self._get_crit_stat_multiplier(
            target_pokemon, defense_stat, is_attacker=False
        )

        crit_attack = int(attacker_stat_value * crit_attack_multiplier)
        crit_defense = int(
            defender_stat_value * crit_defense_multiplier * weather_defense_modifier
        )

        crit_attack = self._modify_attack_for_ability(
            crit_attack,
            attack_stat,
            attacker_ability,
            move_data,
            attacking_pokemon,
            weather,
        )
        crit_defense = self._modify_defense_for_ability(
            crit_defense,
            defense_stat,
            defender_ability,
            target_pokemon,
            ignores_defender_ability,
        )

        crit_base_damage = (
            int(
                int(
                    int(int(2 * level / 5 + 2) * base_power * crit_attack)
                    / crit_defense
                )
                / 50
            )
            + 2
        )

        crit_damage = self._apply_modifiers(
            crit_base_damage,
            attacking_pokemon,
            target_pokemon,
            move_data,
            field_state,
            defender_side_conditions,
            is_crit=True,
            attacker_ability=attacker_ability,
            defender_ability=defender_ability,
            has_target_secondary_effect=has_target_secondary_effect,
        )

        crit_min_damage = int(crit_damage * 0.85)
        crit_max_damage = int(crit_damage * 1.0)

        attacker_item = (
            normalize_name(attacking_pokemon.item) if attacking_pokemon.item else ""
        )
        hit_count, hit_distribution = self._get_multihit_distribution(
            move_data, attacker_ability, attacker_item
        )

        min_hits = min(hits for hits, _ in hit_distribution)
        max_hits = max(hits for hits, _ in hit_distribution)

        min_damage = int(min_damage * min_hits)
        max_damage = int(max_damage * max_hits)
        crit_min_damage = int(crit_min_damage * min_hits)
        crit_max_damage = int(crit_max_damage * max_hits)

        ko_prob = 0.0
        if min_damage >= target_pokemon.current_hp:
            ko_prob = 1.0
        elif max_damage >= target_pokemon.current_hp:
            for hits, hit_prob in hit_distribution:
                min_damage_for_hits = int(damage * 0.85 * hits)
                max_damage_for_hits = int(damage * 1.0 * hits)

                if min_damage_for_hits >= target_pokemon.current_hp:
                    ko_prob += hit_prob
                elif max_damage_for_hits >= target_pokemon.current_hp:
                    damage_range = max_damage_for_hits - min_damage_for_hits
                    if damage_range > 0:
                        ko_roll_prob = (
                            max_damage_for_hits - target_pokemon.current_hp
                        ) / damage_range
                        ko_prob += hit_prob * ko_roll_prob
                    else:
                        ko_prob += hit_prob * 0.5

        status_chances, stat_chances, additional_effects = (
            self._calculate_secondary_effects(
                secondary_effects, attacker_ability, defender_ability
            )
        )

        recoil_tuple = self._get_move_recoil(move_data, move.name)
        drain_tuple = self._get_move_drain(move_data, move.name)

        recoil_damage = self._calculate_recoil_damage(
            recoil_tuple, max_damage, attacking_pokemon
        )
        drain_heal = self._calculate_drain_heal(
            drain_tuple, max_damage, attacking_pokemon, target_pokemon
        )

        return MoveResult(
            min_damage=min_damage,
            max_damage=max_damage,
            knockout_probability=ko_prob,
            critical_hit_probability=crit_chance,
            crit_min_damage=crit_min_damage,
            crit_max_damage=crit_max_damage,
            status_effects=status_chances,
            additional_effects=additional_effects,
            hit_count=hit_count,
            recoil_damage=recoil_damage,
            drain_heal=drain_heal,
            status_infliction_chances=status_chances,
            stat_change_chances=stat_chances,
        )

    def _modify_attack_for_ability(
        self,
        attack_value: int,
        attack_stat: Stat,
        attacker_ability: str,
        move_data,
        attacker: PokemonState,
        weather: Optional[Weather],
    ) -> int:
        modified_attack = attack_value
        if attack_stat == Stat.ATK:
            if attacker_ability in {"hugepower", "purepower"}:
                modified_attack = int(modified_attack * 2.0)
            if (
                attacker_ability == "guts"
                and move_data.category == "Physical"
                and attacker.status != Status.NONE
            ):
                modified_attack = int(modified_attack * 1.5)
            if attacker_ability == "hustle" and move_data.category == "Physical":
                modified_attack = int(modified_attack * 1.5)
        if (
            attack_stat == Stat.SPA
            and attacker_ability == "solarpower"
            and weather == Weather.SUN
        ):
            modified_attack = int(modified_attack * 1.5)
        if attack_stat in {Stat.ATK, Stat.SPA}:
            low_hp_boosts = {
                "overgrow": "Grass",
                "blaze": "Fire",
                "torrent": "Water",
                "swarm": "Bug",
            }
            boosted_type = low_hp_boosts.get(attacker_ability)
            if (
                boosted_type
                and move_data.type == boosted_type
                and attacker.max_hp > 0
                and attacker.current_hp * 3 <= attacker.max_hp
            ):
                modified_attack = int(modified_attack * 1.5)
            if attacker_ability == "steelworker" and move_data.type == "Steel":
                modified_attack = int(modified_attack * 1.5)
            if attacker_ability == "waterbubble" and move_data.type == "Water":
                modified_attack = int(modified_attack * 2.0)
            if (
                attacker_ability == "defeatist"
                and attacker.max_hp > 0
                and attacker.current_hp * 2 <= attacker.max_hp
            ):
                modified_attack = int(modified_attack * 0.5)
            move_flags_list: List[str] = []
            if move_data.flags:
                move_flags_list = list(move_data.flags)
            else:
                fallback_flags = self.MOVE_FLAGS_DATA.get(
                    normalize_name(move_data.name)
                )
                if fallback_flags:
                    move_flags_list = fallback_flags
            move_flags = {flag.lower() for flag in move_flags_list}
            if attacker_ability == "ironfist" and "punch" in move_flags:
                modified_attack = int(modified_attack * 1.2)
            if attacker_ability == "strongjaw" and "bite" in move_flags:
                modified_attack = int(modified_attack * 1.5)
            if attacker_ability == "megalauncher" and (
                "pulse" in move_flags or "aura" in move_flags
            ):
                modified_attack = int(modified_attack * 1.5)
            if attacker_ability == "sharpness" and "slicing" in move_flags:
                modified_attack = int(modified_attack * 1.5)
        return modified_attack

    def _modify_defense_for_ability(
        self,
        defense_value: int,
        defense_stat: Stat,
        defender_ability: str,
        defender: PokemonState,
        ignore_defender_ability: bool,
    ) -> int:
        modified_defense = defense_value
        if ignore_defender_ability:
            return modified_defense
        if defense_stat == Stat.DEF:
            if defender_ability == "furcoat":
                modified_defense = int(modified_defense * 2.0)
            if defender_ability == "marvelscale" and defender.status != Status.NONE:
                modified_defense = int(modified_defense * 1.5)
        return modified_defense

    def _get_crit_stat_multiplier(
        self, pokemon: PokemonState, stat: Stat, is_attacker: bool
    ) -> float:
        boost = pokemon.get_stat_boost(stat)
        if is_attacker:
            boost = max(boost, 0)
        else:
            boost = min(boost, 0)
        return STAT_STAGE_MULTIPLIERS[boost]

    def _get_ability(self, pokemon: PokemonState) -> str:
        return normalize_name(pokemon.ability) if pokemon.ability else ""

    def _get_multihit_distribution(
        self, move_data, attacker_ability: str, attacker_item: str
    ) -> Tuple[Union[int, str], List[Tuple[int, float]]]:
        """Determine effective hit count and distribution for multi-hit moves.

        Accounts for Skill Link (always max hits) and Loaded Dice (4-5 hits).

        Returns:
            Tuple of (hit_count_display, [(hits, probability), ...])
            - hit_count_display: int for fixed hits, str for variable (e.g., "4-5")
            - distribution: list of (hit_count, probability) tuples

        Examples:
            - Skill Link + Bullet Seed: (5, [(5, 1.0)])
            - Loaded Dice + Bullet Seed: ("4-5", [(4, 0.5), (5, 0.5)])
            - Normal Bullet Seed: ("2-5", [(2, 0.35), (3, 0.35), (4, 0.15), (5, 0.15)])
            - Double Kick: (2, [(2, 1.0)])
        """
        if not move_data.multihit:
            return (1, [(1, 1.0)])

        if isinstance(move_data.multihit, int):
            fixed_hits = move_data.multihit
            return (fixed_hits, [(fixed_hits, 1.0)])

        min_hits, max_hits = move_data.multihit

        if attacker_ability == "skilllink":
            return (max_hits, [(max_hits, 1.0)])

        if attacker_item == "loadeddice":
            if min_hits == 2 and max_hits == 5:
                return ("4-5", [(4, 0.5), (5, 0.5)])

        if min_hits == 2 and max_hits == 5:
            return (
                f"{min_hits}-{max_hits}",
                [(2, 0.35), (3, 0.35), (4, 0.15), (5, 0.15)],
            )

        avg_hits = (min_hits + max_hits) / 2
        return (f"{min_hits}-{max_hits}", [(int(avg_hits), 1.0)])

    def _is_grounded(self, pokemon: PokemonState) -> bool:
        ability = self._get_ability(pokemon)
        if ability == "levitate":
            return False

        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        types = pokemon_data.types
        if "Flying" in types:
            return False

        return True

    def _get_weather_stat_modifier(
        self, pokemon: PokemonState, stat: Stat, weather: Optional[Weather]
    ) -> float:
        if not weather or weather == Weather.NONE:
            return 1.0

        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        types = pokemon_data.types

        if stat == Stat.SPD and weather == Weather.SANDSTORM:
            if "Rock" in types:
                return 1.5
        elif stat == Stat.DEF and weather == Weather.SNOW:
            if "Ice" in types:
                return 1.5

        return 1.0

    def _apply_modifiers(
        self,
        base_damage: int,
        attacker: PokemonState,
        defender: PokemonState,
        move_data,
        field_state: Optional[FieldState],
        defender_side_conditions: Optional[List[SideCondition]],
        is_crit: bool,
        attacker_ability: str,
        defender_ability: str,
        has_target_secondary_effect: bool,
    ) -> float:
        damage = float(base_damage)

        ignore_defender_ability = attacker_ability in {
            "moldbreaker",
            "teravolt",
            "turboblaze",
        }
        effective_defender_ability = "" if ignore_defender_ability else defender_ability

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
            stab_multiplier = 2.0 if attacker.has_terastallized else 1.5
            if attacker_ability == "adaptability":
                stab_multiplier = 2.25 if stab_multiplier > 1.5 else 2.0
            damage *= stab_multiplier

        defender_pokemon_data = self.game_data.get_pokemon(defender.species)
        defender_types = defender_pokemon_data.types
        if defender.has_terastallized and defender.tera_type:
            defender_types = [defender.tera_type]

        type_effectiveness = 1.0
        type_chart = self.game_data.get_type_chart()
        for defender_type in defender_types:
            effectiveness = type_chart.get_effectiveness(move_data.type, defender_type)
            if (
                effectiveness == 0.0
                and attacker_ability == "scrappy"
                and defender_type == "Ghost"
                and move_data.type in {"Normal", "Fighting"}
            ):
                effectiveness = 1.0
            type_effectiveness *= effectiveness
        ability_type_immunities = {
            "levitate": {"Ground"},
            "flashfire": {"Fire"},
            "waterabsorb": {"Water"},
            "dryskin": {"Water"},
            "stormdrain": {"Water"},
            "voltabsorb": {"Electric"},
            "lightningrod": {"Electric"},
            "motordrive": {"Electric"},
            "sapsipper": {"Grass"},
        }

        if (
            effective_defender_ability in ability_type_immunities
            and move_data.type in ability_type_immunities[effective_defender_ability]
        ):
            type_effectiveness = 0.0

        damage *= type_effectiveness

        damage *= self._get_item_damage_multiplier(
            attacker, move_data, type_effectiveness
        )

        if attacker_ability == "sheerforce" and has_target_secondary_effect:
            damage *= 1.3

        is_resisted = 0.0 < type_effectiveness < 1.0
        if attacker_ability == "tintedlens" and is_resisted:
            damage *= 2.0

        if (
            attacker.status == Status.BURN
            and move_data.category == "Physical"
            and attacker_ability not in {"guts", "waterbubble"}
        ):
            damage *= 0.5

        if effective_defender_ability == "thickfat" and move_data.type in {
            "Fire",
            "Ice",
        }:
            damage *= 0.5
        if effective_defender_ability == "waterbubble" and move_data.type == "Fire":
            damage *= 0.5
        if effective_defender_ability == "heatproof" and move_data.type == "Fire":
            damage *= 0.5
        if effective_defender_ability == "dryskin" and move_data.type == "Fire":
            damage *= 1.25
        if type_effectiveness > 1.0 and effective_defender_ability in {
            "filter",
            "solidrock",
            "prismarmor",
        }:
            damage *= 0.75
        if (
            effective_defender_ability in {"multiscale", "shadowshield"}
            and defender.max_hp > 0
            and defender.current_hp == defender.max_hp
        ):
            damage *= 0.5
        if (
            effective_defender_ability == "icescales"
            and move_data.category == "Special"
        ):
            damage *= 0.5
        if effective_defender_ability == "purifyingsalt" and move_data.type == "Ghost":
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

    def _get_item_damage_multiplier(
        self, attacker: PokemonState, move_data, type_effectiveness: float
    ) -> float:
        if not attacker.item:
            return 1.0

        item = normalize_name(attacker.item)
        if not item:
            return 1.0

        multiplier = 1.0
        move_category = move_data.category
        move_type = move_data.type

        if item == "lifeorb":
            multiplier *= 1.3
        if item == "choiceband" and move_category == "Physical":
            multiplier *= 1.5
        if item == "choicespecs" and move_category == "Special":
            multiplier *= 1.5

        if item == "expertbelt" and type_effectiveness > 1.0:
            multiplier *= 1.2
        if item == "muscleband" and move_category == "Physical":
            multiplier *= 1.1
        if item == "wiseglasses" and move_category == "Special":
            multiplier *= 1.1

        boosted_type = self.TYPE_BOOST_ITEMS.get(item)
        if boosted_type and move_type == boosted_type:
            multiplier *= 1.2

        species = normalize_name(attacker.species) if attacker.species else ""
        species_boost = self.SPECIES_TYPE_BOOST_ITEMS.get(item)
        if species_boost and species in species_boost["species"]:
            allowed_types = species_boost["types"]
            if allowed_types is None or move_type in allowed_types:
                multiplier *= float(species_boost["multiplier"])

        if item == "lightball" and species.startswith("pikachu"):
            if move_category in {"Physical", "Special"}:
                multiplier *= 2.0

        if (
            item == "thickclub"
            and species
            in {
                "cubone",
                "marowak",
                "marowakalola",
                "marowakalolatotem",
            }
            and move_category == "Physical"
        ):
            multiplier *= 2.0

        if (
            item == "deepseatooth"
            and species == "clamperl"
            and move_category == "Special"
        ):
            multiplier *= 2.0

        return multiplier
