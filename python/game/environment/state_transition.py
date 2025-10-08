"""State transition logic for battle simulation.

This module provides pure functions that apply battle events to create new
immutable battle states. The main entry point is StateTransition.apply().
"""

import json
from dataclasses import replace

from typing import Tuple

from absl import logging

from python.game.events.battle_event import (
    BattleEvent,
    BoostEvent,
    ClearAllBoostEvent,
    ClearBoostEvent,
    ClearNegativeBoostEvent,
    CureStatusEvent,
    DamageEvent,
    DetailsChangeEvent,
    DragEvent,
    FaintEvent,
    FieldEndEvent,
    FieldStartEvent,
    HealEvent,
    ReplaceEvent,
    RequestEvent,
    SetBoostEvent,
    SetHpEvent,
    SideEndEvent,
    SideStartEvent,
    StatusEvent,
    SwitchEvent,
    UnboostEvent,
    UpkeepEvent,
    WeatherEvent,
)
from python.game.schema.battle_state import BattleState
from python.game.schema.enums import (
    FieldEffect,
    SideCondition,
    Stat,
    Status,
    Terrain,
    Weather,
)
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState


class StateTransition:
    """Pure functions for applying events to battle states.

    All methods are static and pure - they take a state and event, return a new
    state, and never mutate the inputs.
    """

    @staticmethod
    def apply(state: BattleState, event: BattleEvent) -> BattleState:
        """Apply an event to a battle state, returning a new state.

        Args:
            state: Current battle state (immutable)
            event: Battle event to apply

        Returns:
            New battle state with event applied (original unchanged)
        """
        if isinstance(event, DamageEvent):
            return StateTransition._apply_damage(state, event)
        elif isinstance(event, HealEvent):
            return StateTransition._apply_heal(state, event)
        elif isinstance(event, SetHpEvent):
            return StateTransition._apply_sethp(state, event)
        elif isinstance(event, SwitchEvent):
            return StateTransition._apply_switch(state, event)
        elif isinstance(event, DragEvent):
            return StateTransition._apply_drag(state, event)
        elif isinstance(event, FaintEvent):
            return StateTransition._apply_faint(state, event)
        elif isinstance(event, ReplaceEvent):
            return StateTransition._apply_replace(state, event)
        elif isinstance(event, DetailsChangeEvent):
            return StateTransition._apply_details_change(state, event)
        elif isinstance(event, BoostEvent):
            return StateTransition._apply_boost(state, event)
        elif isinstance(event, UnboostEvent):
            return StateTransition._apply_unboost(state, event)
        elif isinstance(event, SetBoostEvent):
            return StateTransition._apply_setboost(state, event)
        elif isinstance(event, ClearBoostEvent):
            return StateTransition._apply_clearboost(state, event)
        elif isinstance(event, ClearAllBoostEvent):
            return StateTransition._apply_clearallboost(state, event)
        elif isinstance(event, ClearNegativeBoostEvent):
            return StateTransition._apply_clearnegativeboost(state, event)
        elif isinstance(event, StatusEvent):
            return StateTransition._apply_status(state, event)
        elif isinstance(event, CureStatusEvent):
            return StateTransition._apply_curestatus(state, event)
        elif isinstance(event, WeatherEvent):
            return StateTransition._apply_weather(state, event)
        elif isinstance(event, FieldStartEvent):
            return StateTransition._apply_fieldstart(state, event)
        elif isinstance(event, FieldEndEvent):
            return StateTransition._apply_fieldend(state, event)
        elif isinstance(event, SideStartEvent):
            return StateTransition._apply_sidestart(state, event)
        elif isinstance(event, SideEndEvent):
            return StateTransition._apply_sideend(state, event)
        elif isinstance(event, RequestEvent):
            return StateTransition._apply_request(state, event)
        elif isinstance(event, UpkeepEvent):
            return StateTransition._apply_upkeep(state, event)
        else:
            logging.warning(f"Unknown event: {event}")
            return state

    @staticmethod
    def _parse_stat(stat_str: str) -> Stat:
        """Parse Showdown stat string to Stat enum.

        Args:
            stat_str: Stat string from Showdown protocol

        Returns:
            Stat enum value
        """
        stat_lower = stat_str.lower()
        if stat_lower == "atk":
            return Stat.ATK
        elif stat_lower == "def":
            return Stat.DEF
        elif stat_lower in ["spa", "spatk", "sp.atk"]:
            return Stat.SPA
        elif stat_lower in ["spd", "spdef", "sp.def"]:
            return Stat.SPD
        elif stat_lower in ["spe", "speed"]:
            return Stat.SPE
        elif stat_lower == "accuracy":
            return Stat.ACCURACY
        elif stat_lower == "evasion":
            return Stat.EVASION
        else:
            raise ValueError(f"Unknown stat: {stat_str}")

    @staticmethod
    def _parse_status(status_str: str) -> Status:
        """Parse Showdown status string to Status enum.

        Args:
            status_str: Status string from Showdown protocol

        Returns:
            Status enum value
        """
        if not status_str:
            return Status.NONE

        status_lower = status_str.lower()
        if status_lower in ["brn", "burn"]:
            return Status.BURN
        elif status_lower in ["par", "paralysis"]:
            return Status.PARALYSIS
        elif status_lower in ["psn", "poison"]:
            return Status.POISON
        elif status_lower in ["tox", "toxic"]:
            return Status.TOXIC
        elif status_lower in ["slp", "sleep"]:
            return Status.SLEEP
        elif status_lower in ["frz", "freeze"]:
            return Status.FREEZE
        else:
            raise ValueError(f"Unknown status: {status_str}")

    @staticmethod
    def _get_pokemon_and_team(
        state: BattleState, player_id: str, position: str
    ) -> Tuple[PokemonState, TeamState, str]:
        """Get the pokemon and team for a player position.

        Args:
            state: Current battle state
            player_id: Player ID (p1 or p2)
            position: Position identifier (e.g., "a", "b")

        Returns:
            Tuple of (pokemon, team, player_id)
        """
        team = state.get_team(player_id)

        pokemon_index = 0 if position == "a" else 1

        pokemon = team.get_active_pokemon() if pokemon_index == 0 else None

        if pokemon is None:
            all_pokemon = team.get_pokemon_team()
            if pokemon_index < len(all_pokemon):
                pokemon = all_pokemon[pokemon_index]

        if pokemon is None:
            pokemon = PokemonState(species="Unknown")

        return pokemon, team, player_id

    @staticmethod
    def _update_pokemon_in_team(
        team: TeamState, old_pokemon: PokemonState, new_pokemon: PokemonState
    ) -> TeamState:
        """Replace a pokemon in a team with an updated version.

        Args:
            team: Current team state
            old_pokemon: Pokemon to replace
            new_pokemon: Updated pokemon

        Returns:
            New team state with pokemon replaced
        """
        all_pokemon = list(team.get_pokemon_team())
        found_pokemon = False
        for i, p in enumerate(all_pokemon):
            if p.species == old_pokemon.species and p.nickname == old_pokemon.nickname:
                all_pokemon[i] = new_pokemon
                found_pokemon = True
                break
        if not found_pokemon:
            raise ValueError(
                f"Pokemon {old_pokemon.species} {old_pokemon.nickname} not found in team"
            )

        return replace(team, pokemon=all_pokemon)

    @staticmethod
    def _update_team_in_state(
        state: BattleState, player_id: str, new_team: TeamState
    ) -> BattleState:
        """Update a team in the battle state.

        Args:
            state: Current battle state
            player_id: Player ID (p1 or p2)
            new_team: Updated team state

        Returns:
            New battle state with team updated
        """
        return (
            replace(state, p1_team=new_team)
            if player_id == "p1"
            else replace(state, p2_team=new_team)
        )

    @staticmethod
    def _apply_damage(state: BattleState, event: DamageEvent) -> BattleState:
        """Apply damage to a pokemon.

        Args:
            state: Current battle state
            event: Damage event

        Returns:
            New battle state with damage applied
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        new_pokemon = replace(
            pokemon,
            current_hp=event.hp_current,
            max_hp=event.hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_heal(state: BattleState, event: HealEvent) -> BattleState:
        """Apply healing to a pokemon.

        Args:
            state: Current battle state
            event: Heal event

        Returns:
            New battle state with healing applied
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        new_hp = min(event.hp_current, event.hp_max)
        new_pokemon = replace(
            pokemon,
            current_hp=new_hp,
            max_hp=event.hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_sethp(state: BattleState, event: SetHpEvent) -> BattleState:
        """Set pokemon HP to a specific value.

        Args:
            state: Current battle state
            event: SetHp event

        Returns:
            New battle state with HP set
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        new_pokemon = replace(
            pokemon,
            current_hp=event.hp_current,
            max_hp=event.hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_switch(state: BattleState, event: SwitchEvent) -> BattleState:
        """Apply a switch event.

        Args:
            state: Current battle state
            event: Switch event

        Returns:
            New battle state with pokemon switched in
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        # Preserve persistent attributes (moves, item, ability, tera type)
        # Reset volatile state (stat_boosts, volatile_conditions)
        new_pokemon = replace(
            pokemon,
            species=event.species,
            level=event.level,
            gender=event.gender,
            shiny=event.shiny,
            nickname=event.pokemon_name
            if event.pokemon_name != event.species
            else None,
            current_hp=event.hp_current,
            max_hp=event.hp_max,
            status=status,
            stat_boosts={},
            volatile_conditions={},
            is_active=True,
        )

        all_pokemon = list(team.get_pokemon_team())
        pokemon_found = False

        for i, p in enumerate(all_pokemon):
            if p.species == event.species and (
                not event.pokemon_name
                or p.nickname == event.pokemon_name
                or (not p.nickname and p.species == event.pokemon_name)
            ):
                all_pokemon[i] = new_pokemon
                pokemon_found = True
                break

        if not pokemon_found:
            all_pokemon.append(new_pokemon)

        new_active_index = all_pokemon.index(new_pokemon)

        new_team = replace(
            team,
            pokemon=all_pokemon,
            active_pokemon_index=new_active_index,
        )

        return StateTransition._update_team_in_state(state, event.player_id, new_team)

    @staticmethod
    def _apply_drag(state: BattleState, event: DragEvent) -> BattleState:
        """Apply a forced switch (drag) event.

        Drag is functionally the same as switch - both clear volatiles.

        Args:
            state: Current battle state
            event: Drag event

        Returns:
            New battle state with pokemon dragged in
        """
        switch_event = SwitchEvent(
            raw_message=event.raw_message,
            player_id=event.player_id,
            position=event.position,
            pokemon_name=event.pokemon_name,
            species=event.species,
            level=event.level,
            gender=event.gender,
            shiny=event.shiny,
            hp_current=event.hp_current,
            hp_max=event.hp_max,
            status=event.status,
        )
        return StateTransition._apply_switch(state, switch_event)

    @staticmethod
    def _apply_faint(state: BattleState, event: FaintEvent) -> BattleState:
        """Apply a faint event.

        Args:
            state: Current battle state
            event: Faint event

        Returns:
            New battle state with pokemon fainted
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        new_pokemon = replace(pokemon, current_hp=0)

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_replace(state: BattleState, event: ReplaceEvent) -> BattleState:
        """Apply a replace event (Illusion break, forme change with switch).

        Args:
            state: Current battle state
            event: Replace event

        Returns:
            New battle state with pokemon replaced
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        # Replace event preserves all persistent attributes
        new_pokemon = replace(
            pokemon,
            species=event.species,
            level=event.level,
            gender=event.gender,
            shiny=event.shiny,
            current_hp=event.hp_current,
            max_hp=event.hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_details_change(
        state: BattleState, event: DetailsChangeEvent
    ) -> BattleState:
        """Apply a details change event (forme change without switch).

        Args:
            state: Current battle state
            event: Details change event

        Returns:
            New battle state with pokemon details updated
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        details_parts = event.new_details.split(", ")
        new_species = details_parts[0]
        new_gender = None
        new_shiny = False
        new_level = 100

        for detail in details_parts[1:]:
            if detail.upper() in ["M", "F"]:
                new_gender = detail
            elif detail == "shiny":
                new_shiny = True
            elif detail.startswith("L"):
                new_level = int(detail[1:])

        status = pokemon.status
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        # Details change preserves all persistent attributes (forme change)
        new_pokemon = replace(
            pokemon,
            species=new_species,
            level=new_level,
            gender=new_gender,
            shiny=new_shiny,
            current_hp=event.hp_current,
            max_hp=event.hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_boost(state: BattleState, event: BoostEvent) -> BattleState:
        """Apply stat boost."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        stat = StateTransition._parse_stat(event.stat)
        current_boost = pokemon.stat_boosts.get(stat, 0)
        new_boost = max(-6, min(6, current_boost + event.amount))

        new_boosts = dict(pokemon.stat_boosts)
        new_boosts[stat] = new_boost

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=pokemon.status,
            stat_boosts=new_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_unboost(state: BattleState, event: UnboostEvent) -> BattleState:
        """Apply stat decrease."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        stat = StateTransition._parse_stat(event.stat)
        current_boost = pokemon.stat_boosts.get(stat, 0)
        new_boost = max(-6, min(6, current_boost - event.amount))

        new_boosts = dict(pokemon.stat_boosts)
        new_boosts[stat] = new_boost

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=pokemon.status,
            stat_boosts=new_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_setboost(state: BattleState, event: SetBoostEvent) -> BattleState:
        """Set stat to specific stage."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        stat = StateTransition._parse_stat(event.stat)
        new_boost = max(-6, min(6, event.stage))

        new_boosts = dict(pokemon.stat_boosts)
        new_boosts[stat] = new_boost

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=pokemon.status,
            stat_boosts=new_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_clearboost(state: BattleState, event: ClearBoostEvent) -> BattleState:
        """Clear all stat boosts for a pokemon."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=pokemon.status,
            stat_boosts={},
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_clearallboost(
        state: BattleState, event: ClearAllBoostEvent
    ) -> BattleState:
        """Clear all stat boosts for all pokemon (Haze)."""
        p1_pokemon = []
        for p in state.p1_team.get_pokemon_team():
            p1_pokemon.append(
                PokemonState(
                    species=p.species,
                    level=p.level,
                    gender=p.gender,
                    shiny=p.shiny,
                    nickname=p.nickname,
                    current_hp=p.current_hp,
                    max_hp=p.max_hp,
                    status=p.status,
                    stat_boosts={},
                    moves=p.moves,
                    item=p.item,
                    ability=p.ability,
                    tera_type=p.tera_type,
                    has_terastallized=p.has_terastallized,
                    volatile_conditions=p.volatile_conditions,
                    is_active=p.is_active,
                    active_effects=p.active_effects,
                )
            )

        p2_pokemon = []
        for p in state.p2_team.get_pokemon_team():
            p2_pokemon.append(
                PokemonState(
                    species=p.species,
                    level=p.level,
                    gender=p.gender,
                    shiny=p.shiny,
                    nickname=p.nickname,
                    current_hp=p.current_hp,
                    max_hp=p.max_hp,
                    status=p.status,
                    stat_boosts={},
                    moves=p.moves,
                    item=p.item,
                    ability=p.ability,
                    tera_type=p.tera_type,
                    has_terastallized=p.has_terastallized,
                    volatile_conditions=p.volatile_conditions,
                    is_active=p.is_active,
                    active_effects=p.active_effects,
                )
            )

        new_p1_team = TeamState(
            pokemon=p1_pokemon,
            active_pokemon_index=state.p1_team.active_pokemon_index,
            side_conditions=state.p1_team.side_conditions,
            player_id=state.p1_team.player_id,
        )
        new_p2_team = TeamState(
            pokemon=p2_pokemon,
            active_pokemon_index=state.p2_team.active_pokemon_index,
            side_conditions=state.p2_team.side_conditions,
            player_id=state.p2_team.player_id,
        )

        return replace(state, p1_team=new_p1_team, p2_team=new_p2_team)

    @staticmethod
    def _apply_clearnegativeboost(
        state: BattleState, event: ClearNegativeBoostEvent
    ) -> BattleState:
        """Clear negative stat boosts."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        new_boosts = {
            stat: stage for stat, stage in pokemon.stat_boosts.items() if stage >= 0
        }

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=pokemon.status,
            stat_boosts=new_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_status(state: BattleState, event: StatusEvent) -> BattleState:
        """Apply status condition."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        status = StateTransition._parse_status(event.status)
        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=status,
            stat_boosts=pokemon.stat_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_curestatus(state: BattleState, event: CureStatusEvent) -> BattleState:
        """Cure status condition."""
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        new_pokemon = PokemonState(
            species=pokemon.species,
            level=pokemon.level,
            gender=pokemon.gender,
            shiny=pokemon.shiny,
            nickname=pokemon.nickname,
            current_hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            status=Status.NONE,
            stat_boosts=pokemon.stat_boosts,
            moves=pokemon.moves,
            item=pokemon.item,
            ability=pokemon.ability,
            tera_type=pokemon.tera_type,
            has_terastallized=pokemon.has_terastallized,
            volatile_conditions=pokemon.volatile_conditions,
            is_active=pokemon.is_active,
            active_effects=pokemon.active_effects,
        )
        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_weather(state: BattleState, event: WeatherEvent) -> BattleState:
        """Apply weather change.

        Sets new weather or clears weather. Turn decrement happens in upkeep phase.
        """
        weather_map = {
            "none": Weather.NONE,
            "sun": Weather.SUN,
            "sunnyday": Weather.SUN,
            "rain": Weather.RAIN,
            "raindance": Weather.RAIN,
            "sandstorm": Weather.SANDSTORM,
            "snow": Weather.SNOW,
            "hail": Weather.SNOW,
            "desolateland": Weather.HARSH_SUN,
            "primordialsea": Weather.HEAVY_RAIN,
        }

        weather_str = event.weather.lower().replace(" ", "")
        weather = weather_map.get(weather_str, Weather.NONE)

        # If upkeep message, weather is just being announced, don't change state
        # (turns will be decremented by _apply_upkeep)
        if event.upkeep:
            return state

        # New weather: set to 5 turns (or 0 for none)
        turns = 5 if weather != Weather.NONE else 0

        new_field = replace(
            state.field_state,
            weather=weather,
            weather_turns_remaining=turns,
        )

        return replace(state, field_state=new_field)

    @staticmethod
    def _apply_fieldstart(state: BattleState, event: FieldStartEvent) -> BattleState:
        """Apply field effect start."""
        effect_map = {
            "trickroom": FieldEffect.TRICK_ROOM,
            "magicroom": FieldEffect.MAGIC_ROOM,
            "wonderroom": FieldEffect.WONDER_ROOM,
            "gravity": FieldEffect.GRAVITY,
            "mudsport": FieldEffect.MUD_SPORT,
            "watersport": FieldEffect.WATER_SPORT,
        }

        effect_str = event.effect.lower().replace(" ", "")
        effect = effect_map.get(effect_str)

        if effect:
            new_effects = list(state.field_state.field_effects)
            if effect not in new_effects:
                new_effects.append(effect)
            new_field = replace(state.field_state, field_effects=new_effects)
            return replace(state, field_state=new_field)

        terrain_map = {
            "electricterrain": Terrain.ELECTRIC,
            "grassyterrain": Terrain.GRASSY,
            "psychicterrain": Terrain.PSYCHIC,
            "mistyterrain": Terrain.MISTY,
        }

        terrain = terrain_map.get(effect_str)
        if terrain:
            new_field = replace(
                state.field_state, terrain=terrain, terrain_turns_remaining=5
            )
            return replace(state, field_state=new_field)

        return state

    @staticmethod
    def _apply_fieldend(state: BattleState, event: FieldEndEvent) -> BattleState:
        """Apply field effect end."""
        effect_map = {
            "trickroom": FieldEffect.TRICK_ROOM,
            "magicroom": FieldEffect.MAGIC_ROOM,
            "wonderroom": FieldEffect.WONDER_ROOM,
            "gravity": FieldEffect.GRAVITY,
            "mudsport": FieldEffect.MUD_SPORT,
            "watersport": FieldEffect.WATER_SPORT,
        }

        effect_str = event.effect.lower().replace(" ", "")
        effect = effect_map.get(effect_str)

        if effect and effect in state.field_state.field_effects:
            new_effects = [e for e in state.field_state.field_effects if e != effect]
            new_field = replace(state.field_state, field_effects=new_effects)
            return replace(state, field_state=new_field)

        terrain_map = {
            "electricterrain": Terrain.ELECTRIC,
            "grassyterrain": Terrain.GRASSY,
            "psychicterrain": Terrain.PSYCHIC,
            "mistyterrain": Terrain.MISTY,
        }

        terrain = terrain_map.get(effect_str)
        if terrain and state.field_state.terrain == terrain:
            new_field = replace(
                state.field_state, terrain=Terrain.NONE, terrain_turns_remaining=0
            )
            return replace(state, field_state=new_field)

        return state

    @staticmethod
    def _apply_sidestart(state: BattleState, event: SideStartEvent) -> BattleState:
        """Apply side condition start."""
        condition_map = {
            "reflect": SideCondition.REFLECT,
            "lightscreen": SideCondition.LIGHT_SCREEN,
            "auroraveil": SideCondition.AURORA_VEIL,
            "stealthrock": SideCondition.STEALTH_ROCK,
            "spikes": SideCondition.SPIKES,
            "toxicspikes": SideCondition.TOXIC_SPIKES,
            "stickyweb": SideCondition.STICKY_WEB,
            "tailwind": SideCondition.TAILWIND,
            "safeguard": SideCondition.SAFEGUARD,
            "mist": SideCondition.MIST,
            "luckychant": SideCondition.LUCKY_CHANT,
        }

        condition_str = event.condition.lower().replace(" ", "")
        condition = condition_map.get(condition_str)

        if not condition:
            raise ValueError(f"Unknown side condition: {event.condition}")

        team = state.get_team(event.player_id)
        new_conditions = dict(team.side_conditions)

        if condition in [SideCondition.SPIKES, SideCondition.TOXIC_SPIKES]:
            current = new_conditions.get(condition, 0)
            new_conditions[condition] = min(current + 1, 3)
        else:
            new_conditions[condition] = 1

        new_team = replace(team, side_conditions=new_conditions)
        return StateTransition._update_team_in_state(state, event.player_id, new_team)

    @staticmethod
    def _apply_sideend(state: BattleState, event: SideEndEvent) -> BattleState:
        """Apply side condition end."""
        condition_map = {
            "reflect": SideCondition.REFLECT,
            "lightscreen": SideCondition.LIGHT_SCREEN,
            "auroraveil": SideCondition.AURORA_VEIL,
            "stealthrock": SideCondition.STEALTH_ROCK,
            "spikes": SideCondition.SPIKES,
            "toxicspikes": SideCondition.TOXIC_SPIKES,
            "stickyweb": SideCondition.STICKY_WEB,
            "tailwind": SideCondition.TAILWIND,
            "safeguard": SideCondition.SAFEGUARD,
            "mist": SideCondition.MIST,
            "luckychant": SideCondition.LUCKY_CHANT,
        }

        condition_str = event.condition.lower().replace(" ", "")
        condition = condition_map.get(condition_str)

        if not condition:
            return state

        team = state.get_team(event.player_id)
        new_conditions = dict(team.side_conditions)

        if condition in new_conditions:
            del new_conditions[condition]

        new_team = replace(team, side_conditions=new_conditions)
        return StateTransition._update_team_in_state(state, event.player_id, new_team)

    @staticmethod
    def _apply_request(state: BattleState, event: RequestEvent) -> BattleState:
        """Parse request event to extract available actions.

        Also validates inference logic by comparing inferred vs actual values.
        """
        request_data = json.loads(event.request_json)

        # Infer values from state for validation (assume p1)
        player_id = "p1"
        inferred_moves = StateTransition._infer_available_moves(state, player_id)
        inferred_switches = StateTransition._infer_available_switches(state, player_id)

        available_moves = []
        available_switches = []
        can_mega = False
        can_tera = False
        can_dynamax = False
        force_switch = False

        if "active" in request_data and request_data["active"]:
            active_data = request_data["active"][0]

            if "moves" in active_data:
                for i, move in enumerate(active_data["moves"]):
                    if not move.get("disabled", False):
                        available_moves.append(move.get("move", ""))

            can_mega = active_data.get("canMegaEvo", False)
            can_tera = bool(active_data.get("canTerastallize"))
            can_dynamax = active_data.get("canDynamax", False)

        if "side" in request_data and "pokemon" in request_data["side"]:
            for i, pokemon in enumerate(request_data["side"]["pokemon"]):
                if (
                    not pokemon.get("active", False)
                    and pokemon.get("condition") != "0 fnt"
                ):
                    available_switches.append(i)

        if "forceSwitch" in request_data:
            force_switch = (
                bool(request_data["forceSwitch"][0])
                if request_data["forceSwitch"]
                else False
            )

        if set(inferred_moves) != set(available_moves):
            logging.info(
                f"Move inference diff for {player_id} - "
                f"Inferred: {inferred_moves}, Actual: {available_moves}"
            )

        if set(inferred_switches) != set(available_switches):
            logging.info(
                f"Switch inference diff for {player_id} - "
                f"Inferred: {inferred_switches}, Actual: {available_switches}"
            )

        return replace(
            state,
            available_moves=available_moves,
            available_switches=available_switches,
            can_mega=can_mega,
            can_tera=can_tera,
            can_dynamax=can_dynamax,
            force_switch=force_switch,
        )

    @staticmethod
    def _apply_upkeep(state: BattleState, event: UpkeepEvent) -> BattleState:
        """Apply upkeep phase - decrement all turn-based effects.

        Args:
            state: Current battle state
            event: Upkeep event

        Returns:
            New battle state with turn counters decremented
        """
        field = state.field_state

        # Decrement weather turns if weather is active
        weather_turns = field.weather_turns_remaining
        if field.weather != Weather.NONE and weather_turns > 0:
            weather_turns = max(0, weather_turns - 1)

        # Decrement terrain turns if terrain is active
        terrain_turns = field.terrain_turns_remaining
        if field.terrain != Terrain.NONE and terrain_turns > 0:
            terrain_turns = max(0, terrain_turns - 1)

        # Decrement field effect turns if applicable
        # (Currently not tracking individual field effect turns)

        new_field = replace(
            field,
            weather_turns_remaining=weather_turns,
            terrain_turns_remaining=terrain_turns,
        )

        return replace(state, field_state=new_field)
