"""State transition logic for battle simulation.

This module provides pure functions that apply battle events to create new
immutable battle states. The main entry point is StateTransition.apply().
"""

import json
from dataclasses import replace

from typing import Tuple

from absl import logging

from python.game.data.game_data import GameData
from python.game.events.battle_event import (
    AbilityEvent,
    ActivateEvent,
    BattleEndEvent,
    BattleEvent,
    BattleStartEvent,
    BoostEvent,
    CantEvent,
    ClearAllBoostEvent,
    ClearBoostEvent,
    ClearNegativeBoostEvent,
    ClearPokeEvent,
    CritEvent,
    CureStatusEvent,
    DamageEvent,
    DetailsChangeEvent,
    DragEvent,
    EndAbilityEvent,
    EndItemEvent,
    EndVolatileEvent,
    ErrorEvent,
    FailEvent,
    FaintEvent,
    FieldEndEvent,
    FieldStartEvent,
    FormeChangeEvent,
    GameTypeEvent,
    GenEvent,
    HealEvent,
    HitCountEvent,
    IgnoredEvent,
    ImmuneEvent,
    ItemEvent,
    MissEvent,
    MoveEvent,
    PlayerEvent,
    PokeEvent,
    PrepareEvent,
    PrivateMessageEvent,
    ReplaceEvent,
    RequestEvent,
    ResistedEvent,
    SetBoostEvent,
    SetHpEvent,
    SideEndEvent,
    SideStartEvent,
    SingleMoveEvent,
    SingleTurnEvent,
    StartVolatileEvent,
    StatusEvent,
    SuperEffectiveEvent,
    SwitchEvent,
    TeamPreviewEvent,
    TeamSizeEvent,
    TerastallizeEvent,
    TierEvent,
    TransformEvent,
    TurnEvent,
    UnboostEvent,
    UnknownEvent,
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
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class StateTransition:
    """Functions for applying events to battle states.

    Uses a shared GameData singleton for move PP lookups and other game data queries.
    All methods are static and return new states without mutating inputs.
    """

    # Shared game data instance for looking up move PP
    # Initialize eagerly to catch any initialization errors early
    _game_data: GameData = GameData()

    @staticmethod
    def _calculate_max_pp(move_name: str) -> int:
        """Calculate max PP for a move, assuming PP Ups are maxed.

        Args:
            move_name: Name of the move

        Returns:
            Max PP (base PP * 8/5), or 1 if move not found
        """
        move = StateTransition._game_data.get_move(move_name)
        return int(move.pp * 8 / 5)

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
        elif isinstance(event, PokeEvent):
            return StateTransition._apply_poke(state, event)
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
        elif isinstance(event, PlayerEvent):
            return StateTransition._apply_player(state, event)
        elif isinstance(event, BattleEndEvent):
            return StateTransition._apply_battle_end(state, event)
        elif isinstance(event, MoveEvent):
            return StateTransition._apply_move(state, event)
        elif isinstance(event, AbilityEvent):
            return StateTransition._apply_ability(state, event)
        elif isinstance(event, TurnEvent):
            return StateTransition._apply_turn(state, event)
        # Informational events that don't modify battle state
        elif isinstance(
            event,
            (
                # Battle flow events
                BattleStartEvent,
                # Metadata events
                TeamSizeEvent,
                GenEvent,
                TierEvent,
                GameTypeEvent,
                # Team preview events
                ClearPokeEvent,
                TeamPreviewEvent,
                # Move/damage detail events
                SuperEffectiveEvent,
                ResistedEvent,
                ImmuneEvent,
                CritEvent,
                MissEvent,
                FailEvent,
                HitCountEvent,
                CantEvent,
                PrepareEvent,
                # Item events (informational only, actual effects handled elsewhere)
                EndAbilityEvent,
                ItemEvent,
                EndItemEvent,
                ActivateEvent,
                # Volatile condition events (not currently tracked in state)
                StartVolatileEvent,
                EndVolatileEvent,
                SingleTurnEvent,
                SingleMoveEvent,
                # Form change events (cosmetic, not affecting battle mechanics)
                TerastallizeEvent,
                FormeChangeEvent,
                TransformEvent,
                # Ignored/metadata events
                IgnoredEvent,
                PrivateMessageEvent,
                ErrorEvent,
            ),
        ):
            return state
        # Truly unknown events
        elif isinstance(event, UnknownEvent):
            logging.warning(f"Unknown event: {event}")
            return state
        else:
            # This should never happen if all event types are handled
            logging.error(f"Unhandled event type: {type(event).__name__}: {event}")
            return state

    @staticmethod
    def _normalize_species_name(species: str) -> str:
        """Normalize a Pokemon species name for matching.

        Handles various edge cases in species name formatting:
        - Removes asterisk suffix from team preview (e.g., "Zamazenta-*" → "Zamazenta")
        - Converts to lowercase and removes spaces and hyphens
          (e.g., "Walking Wake" → "walkingwake", "Ting-Lu" → "tinglu")

        Args:
            species: Species name to normalize

        Returns:
            Normalized species name for matching
        """
        # Remove team preview asterisk suffix
        if species.endswith("-*"):
            species = species[:-2]
        # Lowercase and remove spaces and hyphens
        return species.lower().replace(" ", "").replace("-", "")

    @staticmethod
    def _normalize_move_name(move_name: str) -> str:
        """Normalize a move name for matching.

        Converts move names to lowercase and removes spaces and hyphens
        to handle different formatting from events vs requests.
        (e.g., "Swords Dance" → "swordsdance", "Will-O-Wisp" → "willowisp")

        Args:
            move_name: Move name to normalize

        Returns:
            Normalized move name for matching
        """
        return move_name.lower().replace(" ", "").replace("-", "")

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
        # Match by species and nickname to find the Pokemon to update
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
        new_teams = dict(state.teams)
        new_teams[player_id] = new_team
        return replace(state, teams=new_teams)

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
    def _apply_poke(state: BattleState, event: PokeEvent) -> BattleState:
        """Apply a poke event (team preview).

        Creates a placeholder Pokemon with species and basic info.
        HP, stats, moves, and other details will be filled in when Pokemon switches in.

        Args:
            state: Current battle state
            event: Poke event containing species and basic info

        Returns:
            New battle state with Pokemon added to team
        """
        team = state.get_team(event.player_id)
        all_pokemon = list(team.get_pokemon_team())

        # Normalize species name (removes "-*" suffix and normalizes case/spaces)
        # Store the original species name (with asterisk removed) in the Pokemon
        species = event.species
        if species.endswith("-*"):
            species = species[:-2]

        # Check if Pokemon already exists (avoid duplicates)
        normalized_species = StateTransition._normalize_species_name(species)
        for p in all_pokemon:
            if StateTransition._normalize_species_name(p.species) == normalized_species:
                # Already exists, don't add duplicate
                return state

        # Create placeholder Pokemon
        new_pokemon = PokemonState(
            species=species,
            gender=event.gender,
            shiny=event.shiny,
            item=event.item,
            level=100,  # Default level
            current_hp=100,  # Placeholder HP
            max_hp=100,  # Placeholder HP
            status=Status.NONE,
            is_active=False,
        )

        all_pokemon.append(new_pokemon)

        new_team = replace(
            team,
            pokemon=all_pokemon,
        )

        return StateTransition._update_team_in_state(state, event.player_id, new_team)

    @staticmethod
    def _apply_switch(state: BattleState, event: SwitchEvent) -> BattleState:
        """Apply a switch event.

        Args:
            state: Current battle state
            event: Switch event

        Returns:
            New battle state with pokemon switched in
        """
        team = state.get_team(event.player_id)
        all_pokemon = list(team.get_pokemon_team())

        # Mark all Pokemon as inactive first
        for i, p in enumerate(all_pokemon):
            if p.is_active:
                all_pokemon[i] = replace(
                    p, is_active=False, stat_boosts={}, volatile_conditions={}
                )

        # Normalize species and pokemon_name for matching
        normalized_event_species = StateTransition._normalize_species_name(
            event.species
        )
        normalized_pokemon_name = (
            StateTransition._normalize_species_name(event.pokemon_name)
            if event.pokemon_name
            else None
        )

        # Find the Pokemon that's switching in to preserve its learned moves/ability
        existing_pokemon = None
        pokemon_index = None
        for i, p in enumerate(all_pokemon):
            normalized_p_species = StateTransition._normalize_species_name(p.species)
            normalized_p_nickname = (
                StateTransition._normalize_species_name(p.nickname)
                if p.nickname
                else None
            )

            # Match if species matches AND (no nickname or nickname matches or species matches pokemon_name)
            # Also handle case where pokemon_name is a shortened form of species (e.g., "landorus" vs "landorus-therian")
            species_matches = normalized_p_species == normalized_event_species
            nickname_matches = (
                not normalized_pokemon_name
                or normalized_p_nickname == normalized_pokemon_name
                or (
                    not normalized_p_nickname
                    and normalized_p_species == normalized_pokemon_name
                )
                or (
                    not normalized_p_nickname
                    and normalized_pokemon_name in normalized_p_species
                )
            )

            if species_matches and nickname_matches:
                existing_pokemon = p
                pokemon_index = i
                break

        # Parse status from event
        status = existing_pokemon.status if existing_pokemon else Status.NONE
        if event.status is not None:
            status = StateTransition._parse_status(event.status)

        # Create new Pokemon state, preserving learned moves/ability from existing Pokemon
        if existing_pokemon and pokemon_index is not None:
            # Preserve persistent attributes (moves, item, ability, tera type)
            # Reset volatile state (stat_boosts, volatile_conditions)
            new_pokemon = replace(
                existing_pokemon,
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
            all_pokemon[pokemon_index] = new_pokemon
        else:
            # Pokemon not in team yet, create new
            new_pokemon = PokemonState(
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
                is_active=True,
            )
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

        new_pokemon = replace(
            pokemon,
            current_hp=0,
            is_active=False,
            stat_boosts={},
            volatile_conditions={},
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        # Keep active_pokemon_index pointing to the fainted Pokemon
        # It will be cleared when a new Pokemon switches in
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

        # Preserve existing HP if event doesn't specify it (e.g., Illusion break)
        # Check if raw message has HP data (5+ parts) or not (4 parts)
        parts = event.raw_message.split("|")
        has_hp_data = len(parts) > 4 and parts[4]
        hp_current = event.hp_current if has_hp_data else pokemon.current_hp
        hp_max = event.hp_max if has_hp_data else pokemon.max_hp

        # Replace event preserves all persistent attributes
        new_pokemon = replace(
            pokemon,
            species=event.species,
            level=event.level,
            gender=event.gender,
            shiny=event.shiny,
            current_hp=hp_current,
            max_hp=hp_max,
            status=status,
        )

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)

        # If this is an Illusion break (e.g., "scream tail" → "zoroark-hisui"),
        # we may have a placeholder Pokemon from PokeEvent that should be removed
        # to avoid duplicates
        if pokemon.species != event.species:
            all_pokemon = list(new_team.get_pokemon_team())
            normalized_new_species = StateTransition._normalize_species_name(
                event.species
            )

            # Remove any non-active Pokemon with the same species as the revealed Pokemon
            # This handles cases where PokeEvent created a placeholder that we no longer need
            filtered_pokemon = []
            for p in all_pokemon:
                normalized_p_species = StateTransition._normalize_species_name(
                    p.species
                )
                # Keep if it's the active Pokemon (the one we just revealed)
                if p.is_active:
                    filtered_pokemon.append(p)
                # Keep if it's a different species
                elif normalized_p_species != normalized_new_species:
                    filtered_pokemon.append(p)
                # Skip non-active Pokemon with same species (placeholders or old copies)

            new_team = replace(new_team, pokemon=filtered_pokemon)

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
        new_teams = {}

        for player_id, team in state.teams.items():
            cleared_pokemon = []
            for p in team.get_pokemon_team():
                cleared_pokemon.append(
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

            new_teams[player_id] = TeamState(
                pokemon=cleared_pokemon,
                active_pokemon_index=team.active_pokemon_index,
                side_conditions=team.side_conditions,
                player_id=team.player_id,
            )

        return replace(state, teams=new_teams)

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

        # Strip "move: " prefix if present (e.g., "move: stealth rock" -> "stealth rock")
        condition_clean = event.condition
        if condition_clean.lower().startswith("move:"):
            condition_clean = condition_clean[5:].strip()

        condition_str = condition_clean.lower().replace(" ", "")
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

        # Strip "move: " prefix if present (e.g., "move: stealth rock" -> "stealth rock")
        condition_clean = event.condition
        if condition_clean.lower().startswith("move:"):
            condition_clean = condition_clean[5:].strip()

        condition_str = condition_clean.lower().replace(" ", "")
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
    def _apply_move(state: BattleState, event: MoveEvent) -> BattleState:
        """Track opponent moves and decrement PP when used.

        When we observe an opponent using a move:
        1. If the move is not in their moveset yet, add it with calculated PP
        2. Decrement the move's current PP by 1
        This allows us to build up knowledge of opponent Pokemon moves and track PP usage.
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        # Find if this move is already in the Pokemon's moveset
        existing_move_index = None
        for i, move in enumerate(pokemon.moves):
            if move.name == event.move_name:
                existing_move_index = i
                break

        new_moves = list(pokemon.moves)

        if existing_move_index is not None:
            # Move already known, decrement PP
            existing_move = new_moves[existing_move_index]
            new_moves[existing_move_index] = PokemonMove(
                name=existing_move.name,
                current_pp=max(0, existing_move.current_pp - 1),
                max_pp=existing_move.max_pp,
            )
        else:
            # Add the newly discovered move with calculated PP, then decrement by 1
            max_pp = StateTransition._calculate_max_pp(event.move_name)
            new_moves.append(
                PokemonMove(
                    name=event.move_name,
                    current_pp=max(
                        0, max_pp - 1
                    ),  # Start with max_pp - 1 since we just used it
                    max_pp=max_pp,
                )
            )

        new_pokemon = replace(pokemon, moves=new_moves)

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_ability(state: BattleState, event: AbilityEvent) -> BattleState:
        """Track opponent abilities by setting them when revealed.

        When we observe an opponent's ability being activated, we set it on their
        Pokemon if it's not already known. This allows us to learn opponent abilities
        during battle.
        """
        pokemon, team, player_id = StateTransition._get_pokemon_and_team(
            state, event.player_id, event.position
        )

        # Only update if ability is currently unknown (empty string)
        if pokemon.ability:
            # Ability already known, no update needed
            return state

        new_pokemon = replace(pokemon, ability=event.ability)

        new_team = StateTransition._update_pokemon_in_team(team, pokemon, new_pokemon)
        return StateTransition._update_team_in_state(state, player_id, new_team)

    @staticmethod
    def _apply_turn(state: BattleState, event: TurnEvent) -> BattleState:
        """Apply turn event - update turn number.

        Args:
            state: Current battle state
            event: Turn event

        Returns:
            New battle state with turn number updated
        """
        new_field = replace(state.field_state, turn_number=event.turn_number)
        return replace(state, field_state=new_field)

    @staticmethod
    def _apply_request(state: BattleState, event: RequestEvent) -> BattleState:
        """Parse request event to extract available actions.

        Also validates inference logic by comparing inferred vs actual values.
        """
        request_data = json.loads(event.request_json)

        if request_data.get("wait", False):
            logging.debug("Received wait request - opponent is choosing")
            return replace(state, waiting=True)

        team_preview = request_data.get("teamPreview", False)

        player_id = "p1"
        if "side" in request_data and "id" in request_data["side"]:
            player_id = request_data["side"]["id"]

        # Learn our player ID from the first request we receive
        if state.our_player_id is None:
            state = replace(state, our_player_id=player_id)

        inferred_moves = state._infer_available_moves(player_id)
        inferred_switches = state._infer_available_switches(player_id)

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
                    move_name = move.get("move", "")
                    if not move.get("disabled", False) and move_name:
                        available_moves.append(move_name)

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

        # Normalize for comparison to avoid false positives from capitalization
        normalized_inferred_moves = [
            StateTransition._normalize_move_name(m) for m in inferred_moves
        ]
        normalized_available_moves = [
            StateTransition._normalize_move_name(m) for m in available_moves
        ]

        if set(normalized_inferred_moves) != set(normalized_available_moves):
            logging.info(
                f"Move inference diff for {player_id} - "
                f"Inferred: {inferred_moves}, Actual: {available_moves}"
            )

        if set(inferred_switches) != set(available_switches):
            logging.info(
                f"Switch inference diff for {player_id} - "
                f"Inferred: {inferred_switches}, Actual: {available_switches}"
            )

        # Populate/update team from request data (for both teams)
        updated_state = state
        team = state.get_team(player_id)

        if "side" in request_data and "pokemon" in request_data["side"]:
            request_pokemon = request_data["side"]["pokemon"]

            existing_pokemon_map = {}
            for poke in team.pokemon:
                # Use normalized species name for matching to handle case differences
                normalized_species = StateTransition._normalize_species_name(
                    poke.species
                )
                key = (normalized_species, poke.nickname)
                existing_pokemon_map[key] = poke

            # Always update team Pokemon from request data to ensure state is current
            new_team_pokemon = []
            for poke_data in request_pokemon:
                condition = poke_data.get("condition", "100/100")
                condition_parts = condition.split()
                hp_parts = condition_parts[0].split("/")
                current_hp = (
                    int(hp_parts[0])
                    if hp_parts[0] != "0" and hp_parts[0] != "fnt"
                    else 0
                )
                max_hp = int(hp_parts[1]) if len(hp_parts) > 1 else 100

                # Parse status from condition (e.g., "100/100 par" -> "par")
                # Note: "0 fnt" format has "fnt" as second part but it's not a status
                status_str = None
                if len(condition_parts) > 1 and condition_parts[1] != "fnt":
                    status_str = condition_parts[1]

                status = Status.NONE
                if status_str:
                    try:
                        status = Status(status_str)
                    except ValueError:
                        status = Status.NONE

                ident = poke_data.get("ident", "")
                nickname = ident.split(": ")[1] if ": " in ident else None

                details = poke_data.get("details", "")
                details_parts = details.split(", ")
                species = details_parts[0] if details_parts else "Unknown"
                gender = details_parts[1] if len(details_parts) > 1 else None

                pokemon_moves = []
                for move_name in poke_data.get("moves", []):
                    # Calculate max PP assuming PP Ups are maxed (8/5 multiplier)
                    max_pp = StateTransition._calculate_max_pp(move_name)
                    pokemon_moves.append(
                        PokemonMove(name=move_name, current_pp=max_pp, max_pp=max_pp)
                    )

                item = poke_data.get("item", "")
                ability = poke_data.get("ability", "")
                tera_type = poke_data.get("teraType", None)

                nickname_key = nickname if nickname != species else None
                # Use normalized species name for lookup to match the key format
                normalized_species = StateTransition._normalize_species_name(species)
                poke_key = (normalized_species, nickname_key)
                existing_pokemon = existing_pokemon_map.get(poke_key)

                if existing_pokemon:
                    pokemon = replace(
                        existing_pokemon,
                        current_hp=current_hp,
                        max_hp=max_hp,
                        status=status,
                        moves=pokemon_moves,
                        item=item if item else None,
                        ability=ability,
                        tera_type=tera_type,
                        is_active=False,  # Will be set to True later if this is the active Pokemon
                    )
                else:
                    pokemon = PokemonState(
                        species=species,
                        level=100,
                        gender=gender,
                        current_hp=current_hp,
                        max_hp=max_hp,
                        status=status,
                        nickname=nickname_key,
                        moves=pokemon_moves,
                        item=item if item else None,
                        ability=ability,
                        tera_type=tera_type,
                    )
                new_team_pokemon.append(pokemon)

            active_index = None
            for i, poke_data in enumerate(request_pokemon):
                if poke_data.get("active", False):
                    active_index = i
                    break

            # Mark the active Pokemon as is_active=True (only if alive)
            if active_index is not None:
                active_pokemon = new_team_pokemon[active_index]
                # Only mark as active if Pokemon is alive
                if active_pokemon.current_hp > 0:
                    new_team_pokemon[active_index] = replace(
                        active_pokemon, is_active=True
                    )

            updated_team = replace(
                team, pokemon=new_team_pokemon, active_pokemon_index=active_index
            )

            updated_state = StateTransition._update_team_in_state(
                state, player_id, updated_team
            )
            team = updated_team

        if "active" in request_data and request_data["active"]:
            active_data = request_data["active"][0]
            if "moves" in active_data:
                # Get the team that was just updated above (which has correct active_index)
                team = updated_state.get_team(player_id)

                # Use the active_pokemon_index from the team to get the correct active Pokemon
                # IMPORTANT: Don't use get_active_pokemon() because it might use a stale index
                if (
                    team.active_pokemon_index is not None
                    and team.active_pokemon_index < len(team.pokemon)
                ):
                    active_pokemon = team.pokemon[team.active_pokemon_index]

                    pokemon_moves = []
                    for move_data in active_data["moves"]:
                        move_name = move_data.get("move", "")
                        if move_name:
                            pokemon_moves.append(
                                PokemonMove(
                                    name=move_name,
                                    current_pp=move_data.get("pp", 0),
                                    max_pp=move_data.get("maxpp", 0),
                                )
                            )

                    choice_items = ["choicescarf", "choicespecs", "choiceband"]
                    pokemon_item = (
                        active_pokemon.item.lower() if active_pokemon.item else ""
                    )
                    has_choice_item = pokemon_item in choice_items
                    choice_locked_move = None
                    if has_choice_item:
                        enabled_moves = []
                        for move_data in active_data["moves"]:
                            if not move_data.get("disabled", False):
                                enabled_moves.append(move_data.get("move", ""))
                        if len(enabled_moves) == 1:
                            choice_locked_move = enabled_moves[0]

                    new_volatile_conditions = dict(active_pokemon.volatile_conditions)
                    if choice_locked_move:
                        new_volatile_conditions["choice_locked_move"] = (
                            choice_locked_move
                        )
                    elif "choice_locked_move" in new_volatile_conditions:
                        del new_volatile_conditions["choice_locked_move"]

                    updated_pokemon = replace(
                        active_pokemon,
                        moves=pokemon_moves,
                        volatile_conditions=new_volatile_conditions,
                    )

                    team_pokemon = list(team.pokemon)
                    team_pokemon[team.active_pokemon_index] = updated_pokemon
                    updated_team = replace(team, pokemon=team_pokemon)

                    updated_state = StateTransition._update_team_in_state(
                        updated_state, player_id, updated_team
                    )

        # Only update available actions if this is our request
        # (we could be p1 or p2, determined from first request)
        if player_id == updated_state.our_player_id:
            return replace(
                updated_state,
                available_moves=available_moves,
                available_switches=available_switches,
                can_mega=can_mega,
                can_tera=can_tera,
                can_dynamax=can_dynamax,
                force_switch=force_switch,
                team_preview=team_preview,
                waiting=False,  # Clear waiting flag when we receive a real request
            )
        else:
            # Not our request, just return updated team data
            return updated_state

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

    @staticmethod
    def _apply_player(state: BattleState, event: "PlayerEvent") -> BattleState:
        """Apply player event - track player usernames.

        Args:
            state: Current battle state
            event: Player event

        Returns:
            New battle state with player username recorded
        """
        new_usernames = dict(state.player_usernames)
        new_usernames[event.player_id] = event.username
        return replace(state, player_usernames=new_usernames)

    @staticmethod
    def _apply_battle_end(state: BattleState, event: "BattleEndEvent") -> BattleState:
        """Apply battle end event - mark battle as over with winner.

        Args:
            state: Current battle state
            event: Battle end event

        Returns:
            New battle state with battle_over=True and winner set
        """
        return replace(state, battle_over=True, winner=event.winner)
