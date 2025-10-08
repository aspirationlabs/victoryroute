from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class BattleEvent(ABC):
    @classmethod
    @abstractmethod
    def parse_raw_message(cls, raw_message: str) -> "BattleEvent":
        pass


@dataclass(frozen=True)
class TurnEvent(BattleEvent):
    raw_message: str
    turn_number: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TurnEvent":
        parts = raw_message.split("|")
        turn_number = int(parts[2])
        return cls(raw_message=raw_message, turn_number=turn_number)


@dataclass(frozen=True)
class BattleStartEvent(BattleEvent):
    raw_message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "BattleStartEvent":
        return cls(raw_message=raw_message)


@dataclass(frozen=True)
class BattleEndEvent(BattleEvent):
    raw_message: str
    winner: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "BattleEndEvent":
        parts = raw_message.split("|")
        winner = parts[2]
        return cls(raw_message=raw_message, winner=winner)


@dataclass(frozen=True)
class PlayerEvent(BattleEvent):
    raw_message: str
    player_id: str
    username: str
    avatar: str
    rating: Optional[int] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "PlayerEvent":
        parts = raw_message.split("|")
        player_id = parts[2]
        username = parts[3]
        avatar = parts[4] if len(parts) > 4 else ""
        rating = int(parts[5]) if len(parts) > 5 and parts[5] else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            username=username,
            avatar=avatar,
            rating=rating,
        )


@dataclass(frozen=True)
class TeamSizeEvent(BattleEvent):
    raw_message: str
    player_id: str
    size: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TeamSizeEvent":
        parts = raw_message.split("|")
        player_id = parts[2]
        size = int(parts[3])
        return cls(raw_message=raw_message, player_id=player_id, size=size)


@dataclass(frozen=True)
class GenEvent(BattleEvent):
    raw_message: str
    generation: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "GenEvent":
        parts = raw_message.split("|")
        generation = int(parts[2])
        return cls(raw_message=raw_message, generation=generation)


@dataclass(frozen=True)
class TierEvent(BattleEvent):
    raw_message: str
    tier: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TierEvent":
        parts = raw_message.split("|")
        tier = parts[2]
        return cls(raw_message=raw_message, tier=tier)


@dataclass(frozen=True)
class GameTypeEvent(BattleEvent):
    raw_message: str
    game_type: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "GameTypeEvent":
        parts = raw_message.split("|")
        game_type = parts[2]
        return cls(raw_message=raw_message, game_type=game_type)


@dataclass(frozen=True)
class SwitchEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    species: str
    level: int
    gender: Optional[str]
    shiny: bool
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SwitchEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        details_parts = parts[3].split(", ")
        species = details_parts[0]
        gender = None
        shiny = False
        level = 100

        for detail in details_parts[1:]:
            if detail.upper() in ["M", "F"]:
                gender = detail
            elif detail == "shiny":
                shiny = True
            elif detail.startswith("L"):
                level = int(detail[1:])

        hp_parts = parts[4].split("/")
        hp_status_parts = hp_parts[1].split(" ") if "/" in parts[4] else ["100", ""]
        hp_current = (
            int(hp_parts[0]) if hp_parts[0] != "0" and hp_parts[0] != "fnt" else 0
        )
        hp_max = (
            int(hp_status_parts[0])
            if hp_status_parts[0] and hp_status_parts[0] != "fnt"
            else 100
        )
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            species=species,
            level=level,
            gender=gender,
            shiny=shiny,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class DragEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    species: str
    level: int
    gender: Optional[str]
    shiny: bool
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "DragEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        details_parts = parts[3].split(", ")
        species = details_parts[0]
        gender = None
        shiny = False
        level = 100

        for detail in details_parts[1:]:
            if detail.upper() in ["M", "F"]:
                gender = detail
            elif detail == "shiny":
                shiny = True
            elif detail.startswith("L"):
                level = int(detail[1:])

        hp_parts = parts[4].split("/")
        hp_status_parts = hp_parts[1].split(" ") if "/" in parts[4] else ["100", ""]
        hp_current = (
            int(hp_parts[0]) if hp_parts[0] != "0" and hp_parts[0] != "fnt" else 0
        )
        hp_max = (
            int(hp_status_parts[0])
            if hp_status_parts[0] and hp_status_parts[0] != "fnt"
            else 100
        )
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            species=species,
            level=level,
            gender=gender,
            shiny=shiny,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class DamageEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    hp_current: int
    hp_max: int
    status: Optional[str]
    source: Optional[str] = None
    source_pokemon: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "DamageEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        hp_string = parts[3]
        if "fnt" in hp_string and "/" not in hp_string:
            hp_current = 0
            hp_max = 100
            status = None
        elif "/" in hp_string:
            hp_parts = hp_string.split("/")
            hp_current = int(hp_parts[0])
            hp_status_parts = hp_parts[1].split(" ")
            hp_max = int(hp_status_parts[0])
            status = (
                hp_status_parts[1]
                if len(hp_status_parts) > 1 and hp_status_parts[1]
                else None
            )
        else:
            hp_current = int(hp_string)
            hp_max = 100
            status = None

        source = None
        source_pokemon = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                source = parts[i][6:] if len(parts[i]) > 6 else None
            elif parts[i].startswith("[of]"):
                of_ident = parts[i][4:] if len(parts[i]) > 4 else ""
                if ": " in of_ident:
                    source_pokemon = of_ident.split(": ")[1]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
            source=source,
            source_pokemon=source_pokemon,
        )


@dataclass(frozen=True)
class HealEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    hp_current: int
    hp_max: int
    status: Optional[str]
    source: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "HealEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        hp_parts = parts[3].split("/")
        hp_status_parts = hp_parts[1].split(" ") if len(hp_parts) > 1 else ["100", ""]
        hp_current = int(hp_parts[0])
        hp_max = int(hp_status_parts[0]) if hp_status_parts[0] else 100
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        source = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                source = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
            source=source,
        )


@dataclass(frozen=True)
class FaintEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "FaintEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class StatusEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    status: str
    source: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "StatusEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        status = parts[3]

        source = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                source = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            status=status,
            source=source,
        )


@dataclass(frozen=True)
class CureStatusEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    status: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "CureStatusEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        status = parts[3]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            status=status,
        )


@dataclass(frozen=True)
class MoveEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    move_name: str
    target_player: Optional[str] = None
    target_position: Optional[str] = None
    target_name: Optional[str] = None
    spread: bool = False
    still: bool = False
    anim: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "MoveEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        move_name = parts[3]

        target_player = None
        target_position = None
        target_name = None
        if len(parts) > 4 and parts[4] and not parts[4].startswith("["):
            target_ident_parts = parts[4].split(": ")
            target_player = target_ident_parts[0][:2]
            target_position = target_ident_parts[0][2:]
            target_name = target_ident_parts[1] if len(target_ident_parts) > 1 else ""

        spread = False
        still = False
        anim = None
        for i in range(4, len(parts)):
            if parts[i] == "[spread]":
                spread = True
            elif parts[i] == "[still]":
                still = True
            elif parts[i].startswith("[anim]"):
                anim = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            move_name=move_name,
            target_player=target_player,
            target_position=target_position,
            target_name=target_name,
            spread=spread,
            still=still,
            anim=anim,
        )


@dataclass(frozen=True)
class BoostEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    stat: str
    amount: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "BoostEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        stat = parts[3]
        amount = int(parts[4])

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            stat=stat,
            amount=amount,
        )


@dataclass(frozen=True)
class UnboostEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    stat: str
    amount: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "UnboostEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        stat = parts[3]
        amount = int(parts[4])

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            stat=stat,
            amount=amount,
        )


@dataclass(frozen=True)
class SetBoostEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    stat: str
    stage: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SetBoostEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        stat = parts[3]
        stage = int(parts[4])

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            stat=stat,
            stage=stage,
        )


@dataclass(frozen=True)
class ClearBoostEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ClearBoostEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class ClearAllBoostEvent(BattleEvent):
    raw_message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ClearAllBoostEvent":
        return cls(raw_message=raw_message)


@dataclass(frozen=True)
class ClearNegativeBoostEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ClearNegativeBoostEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class AbilityEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    ability: str
    trigger: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "AbilityEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        ability = parts[3]

        trigger = None
        if len(parts) > 4 and parts[4] and not parts[4].startswith("["):
            trigger = parts[4]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            ability=ability,
            trigger=trigger,
        )


@dataclass(frozen=True)
class EndAbilityEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    ability: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "EndAbilityEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        ability = parts[3]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            ability=ability,
        )


@dataclass(frozen=True)
class ItemEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    item: str
    trigger: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ItemEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        item = parts[3]

        trigger = None
        if len(parts) > 4 and parts[4] and not parts[4].startswith("["):
            trigger = parts[4]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            item=item,
            trigger=trigger,
        )


@dataclass(frozen=True)
class EndItemEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    item: str
    reason: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "EndItemEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        item = parts[3]

        reason = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                reason = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            item=item,
            reason=reason,
        )


@dataclass(frozen=True)
class StartVolatileEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    condition: str
    silent: bool = False
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "StartVolatileEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        condition = parts[3]

        silent = False
        for i in range(4, len(parts)):
            if parts[i] == "[silent]":
                silent = True

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            condition=condition,
            silent=silent,
        )


@dataclass(frozen=True)
class EndVolatileEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    condition: str
    silent: bool = False
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "EndVolatileEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        condition = parts[3]

        silent = False
        for i in range(4, len(parts)):
            if parts[i] == "[silent]":
                silent = True

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            condition=condition,
            silent=silent,
        )


@dataclass(frozen=True)
class SingleTurnEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    effect: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SingleTurnEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        effect = parts[3]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            effect=effect,
        )


@dataclass(frozen=True)
class SingleMoveEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    effect: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SingleMoveEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        effect = parts[3]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            effect=effect,
        )


@dataclass(frozen=True)
class WeatherEvent(BattleEvent):
    raw_message: str
    weather: str
    upkeep: bool = False
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "WeatherEvent":
        parts = raw_message.split("|")
        weather = parts[2]

        upkeep = False
        for i in range(3, len(parts)):
            if parts[i] == "[upkeep]":
                upkeep = True

        return cls(
            raw_message=raw_message,
            weather=weather,
            upkeep=upkeep,
        )


@dataclass(frozen=True)
class FieldStartEvent(BattleEvent):
    raw_message: str
    effect: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "FieldStartEvent":
        parts = raw_message.split("|")
        effect = parts[2]
        return cls(raw_message=raw_message, effect=effect)


@dataclass(frozen=True)
class FieldEndEvent(BattleEvent):
    raw_message: str
    effect: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "FieldEndEvent":
        parts = raw_message.split("|")
        effect = parts[2]
        return cls(raw_message=raw_message, effect=effect)


@dataclass(frozen=True)
class SideStartEvent(BattleEvent):
    raw_message: str
    player_id: str
    condition: str
    layers: Optional[int] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SideStartEvent":
        parts = raw_message.split("|")
        player_id = parts[2].split(":")[0]
        condition = parts[3]

        layers = None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            condition=condition,
            layers=layers,
        )


@dataclass(frozen=True)
class SideEndEvent(BattleEvent):
    raw_message: str
    player_id: str
    condition: str
    source: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SideEndEvent":
        parts = raw_message.split("|")
        player_id = parts[2].split(":")[0]
        condition = parts[3]

        source = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                source = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            condition=condition,
            source=source,
        )


@dataclass(frozen=True)
class TerastallizeEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    tera_type: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TerastallizeEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        tera_type = parts[3]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            tera_type=tera_type,
        )


@dataclass(frozen=True)
class FormeChangeEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    new_species: str
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "FormeChangeEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        new_species = parts[3]

        hp_parts = parts[4].split("/") if len(parts) > 4 else ["100", "100"]
        hp_status_parts = hp_parts[1].split(" ") if len(hp_parts) > 1 else ["100", ""]
        hp_current = int(hp_parts[0]) if hp_parts[0] else 100
        hp_max = int(hp_status_parts[0]) if hp_status_parts[0] else 100
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            new_species=new_species,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class TransformEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    target_player: str
    target_position: str
    target_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TransformEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        target_ident_parts = parts[3].split(": ")
        target_player = target_ident_parts[0][:2]
        target_position = target_ident_parts[0][2:]
        target_name = target_ident_parts[1] if len(target_ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            target_player=target_player,
            target_position=target_position,
            target_name=target_name,
        )


@dataclass(frozen=True)
class ActivateEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    effect: str
    source: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ActivateEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        effect = parts[3]

        source = None
        for i in range(4, len(parts)):
            if parts[i].startswith("[from]"):
                source = parts[i][6:] if len(parts[i]) > 6 else None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            effect=effect,
            source=source,
        )


@dataclass(frozen=True)
class PrepareEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    move_name: str
    target_player: Optional[str] = None
    target_position: Optional[str] = None
    target_name: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "PrepareEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        move_name = parts[3]

        target_player = None
        target_position = None
        target_name = None
        if len(parts) > 4 and parts[4] and not parts[4].startswith("["):
            target_ident_parts = parts[4].split(": ")
            target_player = target_ident_parts[0][:2]
            target_position = target_ident_parts[0][2:]
            target_name = target_ident_parts[1] if len(target_ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            move_name=move_name,
            target_player=target_player,
            target_position=target_position,
            target_name=target_name,
        )


@dataclass(frozen=True)
class CantEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    reason: str
    move_name: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "CantEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        reason = parts[3]
        move_name = (
            parts[4]
            if len(parts) > 4 and parts[4] and not parts[4].startswith("[")
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            reason=reason,
            move_name=move_name,
        )


@dataclass(frozen=True)
class SuperEffectiveEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SuperEffectiveEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class ResistedEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ResistedEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class ImmuneEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ImmuneEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class CritEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "CritEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class MissEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "MissEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class FailEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "FailEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
        )


@dataclass(frozen=True)
class HitCountEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    count: int
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "HitCountEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        count = int(parts[3])

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            count=count,
        )


@dataclass(frozen=True)
class SetHpEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "SetHpEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        hp_parts = parts[3].split("/")
        hp_status_parts = hp_parts[1].split(" ") if len(hp_parts) > 1 else ["100", ""]
        hp_current = int(hp_parts[0])
        hp_max = int(hp_status_parts[0]) if hp_status_parts[0] else 100
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class ReplaceEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    species: str
    level: int
    gender: Optional[str]
    shiny: bool
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ReplaceEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        details_parts = parts[3].split(", ")
        species = details_parts[0]
        gender = None
        shiny = False
        level = 100

        for detail in details_parts[1:]:
            if detail.upper() in ["M", "F"]:
                gender = detail
            elif detail == "shiny":
                shiny = True
            elif detail.startswith("L"):
                level = int(detail[1:])

        # HP data is optional in replace events
        if len(parts) > 4 and parts[4]:
            hp_parts = parts[4].split("/")
            hp_status_parts = hp_parts[1].split(" ") if "/" in parts[4] else ["100", ""]
            hp_current = (
                int(hp_parts[0]) if hp_parts[0] != "0" and hp_parts[0] != "fnt" else 0
            )
            hp_max = (
                int(hp_status_parts[0])
                if hp_status_parts[0] and hp_status_parts[0] != "fnt"
                else 100
            )
            status = (
                hp_status_parts[1]
                if len(hp_status_parts) > 1 and hp_status_parts[1]
                else None
            )
        else:
            # No HP data provided
            hp_current = 100
            hp_max = 100
            status = None

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            species=species,
            level=level,
            gender=gender,
            shiny=shiny,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class DetailsChangeEvent(BattleEvent):
    raw_message: str
    player_id: str
    position: str
    pokemon_name: str
    new_details: str
    hp_current: int
    hp_max: int
    status: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "DetailsChangeEvent":
        parts = raw_message.split("|")
        ident_parts = parts[2].split(": ")
        player_id = ident_parts[0][:2]
        position = ident_parts[0][2:]
        pokemon_name = ident_parts[1] if len(ident_parts) > 1 else ""

        new_details = parts[3]

        hp_parts = parts[4].split("/") if len(parts) > 4 else ["100", "100"]
        hp_status_parts = hp_parts[1].split(" ") if len(hp_parts) > 1 else ["100", ""]
        hp_current = int(hp_parts[0]) if hp_parts[0] else 100
        hp_max = int(hp_status_parts[0]) if hp_status_parts[0] else 100
        status = (
            hp_status_parts[1]
            if len(hp_status_parts) > 1 and hp_status_parts[1]
            else None
        )

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            position=position,
            pokemon_name=pokemon_name,
            new_details=new_details,
            hp_current=hp_current,
            hp_max=hp_max,
            status=status,
        )


@dataclass(frozen=True)
class PokeEvent(BattleEvent):
    raw_message: str
    player_id: str
    species: str
    gender: Optional[str]
    shiny: bool
    item: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "PokeEvent":
        parts = raw_message.split("|")
        player_id = parts[2]

        details_parts = parts[3].split(", ")
        species = details_parts[0]
        gender = None
        shiny = False
        item = None

        for detail in details_parts[1:]:
            if detail.upper() in ["M", "F"]:
                gender = detail
            elif detail == "shiny":
                shiny = True

        if len(parts) > 4 and parts[4]:
            item = parts[4]

        return cls(
            raw_message=raw_message,
            player_id=player_id,
            species=species,
            gender=gender,
            shiny=shiny,
            item=item,
        )


@dataclass(frozen=True)
class ClearPokeEvent(BattleEvent):
    raw_message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ClearPokeEvent":
        return cls(raw_message=raw_message)


@dataclass(frozen=True)
class TeamPreviewEvent(BattleEvent):
    raw_message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "TeamPreviewEvent":
        return cls(raw_message=raw_message)


@dataclass(frozen=True)
class UpkeepEvent(BattleEvent):
    raw_message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "UpkeepEvent":
        return cls(raw_message=raw_message)


@dataclass(frozen=True)
class RequestEvent(BattleEvent):
    raw_message: str
    request_json: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "RequestEvent":
        parts = raw_message.split("|")
        request_json = parts[2] if len(parts) > 2 else "{}"
        return cls(raw_message=raw_message, request_json=request_json)


@dataclass(frozen=True)
class PrivateMessageEvent(BattleEvent):
    raw_message: str
    sender: str
    recipient: str
    message: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "PrivateMessageEvent":
        parts = raw_message.split("|")
        sender = parts[2] if len(parts) > 2 else ""
        recipient = parts[3] if len(parts) > 3 else ""
        message = parts[4] if len(parts) > 4 else ""
        return cls(
            raw_message=raw_message,
            sender=sender,
            recipient=recipient,
            message=message,
        )


@dataclass(frozen=True)
class PopupEvent(BattleEvent):
    """Event for popup messages from the server (usually errors or notifications)."""

    raw_message: str
    popup_text: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "PopupEvent":
        parts = raw_message.split("|")
        # Join all parts after |popup| to get the full message including newlines
        popup_text = "|".join(parts[2:]) if len(parts) > 2 else ""
        return cls(raw_message=raw_message, popup_text=popup_text)


@dataclass(frozen=True)
class ErrorEvent(BattleEvent):
    """Event for error messages from the server."""

    raw_message: str
    error_text: str
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "ErrorEvent":
        parts = raw_message.split("|")
        # Join all parts after |error| to get the full error message
        error_text = "|".join(parts[2:]) if len(parts) > 2 else ""
        return cls(raw_message=raw_message, error_text=error_text)


@dataclass(frozen=True)
class UnknownEvent(BattleEvent):
    raw_message: str
    message_type: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "UnknownEvent":
        parts = raw_message.split("|")
        message_type = parts[1] if len(parts) > 1 else None
        return cls(raw_message=raw_message, message_type=message_type)


@dataclass(frozen=True)
class IgnoredEvent(BattleEvent):
    """Event for known message types that are metadata/UI and can be ignored."""

    raw_message: str
    message_type: Optional[str] = None
    timestamp: Optional[datetime] = None

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "IgnoredEvent":
        parts = raw_message.split("|")
        message_type = parts[1] if len(parts) > 1 else None
        return cls(raw_message=raw_message, message_type=message_type)
