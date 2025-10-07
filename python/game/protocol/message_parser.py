from typing import Dict, Type

from absl import logging

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
    CureStatusEvent,
    DamageEvent,
    DragEvent,
    EndAbilityEvent,
    EndItemEvent,
    EndVolatileEvent,
    FaintEvent,
    FieldEndEvent,
    FieldStartEvent,
    FormeChangeEvent,
    GameTypeEvent,
    GenEvent,
    HealEvent,
    ItemEvent,
    MoveEvent,
    PlayerEvent,
    PrepareEvent,
    SetBoostEvent,
    SideEndEvent,
    SideStartEvent,
    SingleMoveEvent,
    SingleTurnEvent,
    StartVolatileEvent,
    StatusEvent,
    SwitchEvent,
    TeamSizeEvent,
    TerastallizeEvent,
    TierEvent,
    TransformEvent,
    TurnEvent,
    UnboostEvent,
    UnknownEvent,
    WeatherEvent,
)


class MessageParser:
    MESSAGE_TYPE_MAP: Dict[str, Type[BattleEvent]] = {
        "turn": TurnEvent,
        "start": BattleStartEvent,
        "win": BattleEndEvent,
        "player": PlayerEvent,
        "teamsize": TeamSizeEvent,
        "gen": GenEvent,
        "tier": TierEvent,
        "gametype": GameTypeEvent,
        "switch": SwitchEvent,
        "drag": DragEvent,
        "-damage": DamageEvent,
        "-heal": HealEvent,
        "faint": FaintEvent,
        "-status": StatusEvent,
        "-curestatus": CureStatusEvent,
        "move": MoveEvent,
        "-boost": BoostEvent,
        "-unboost": UnboostEvent,
        "-setboost": SetBoostEvent,
        "-clearboost": ClearBoostEvent,
        "-clearallboost": ClearAllBoostEvent,
        "-clearnegativeboost": ClearNegativeBoostEvent,
        "-ability": AbilityEvent,
        "-endability": EndAbilityEvent,
        "-item": ItemEvent,
        "-enditem": EndItemEvent,
        "-start": StartVolatileEvent,
        "-end": EndVolatileEvent,
        "-singleturn": SingleTurnEvent,
        "-singlemove": SingleMoveEvent,
        "-weather": WeatherEvent,
        "-fieldstart": FieldStartEvent,
        "-fieldend": FieldEndEvent,
        "-sidestart": SideStartEvent,
        "-sideend": SideEndEvent,
        "-terastallize": TerastallizeEvent,
        "-formechange": FormeChangeEvent,
        "-transform": TransformEvent,
        "-activate": ActivateEvent,
        "-prepare": PrepareEvent,
        "cant": CantEvent,
    }

    def parse(self, raw_message: str) -> BattleEvent:
        parts = raw_message.split("|")
        message_type = parts[1] if len(parts) > 1 else ""

        event_class = self.MESSAGE_TYPE_MAP.get(message_type)
        if event_class:
            return event_class.parse_raw_message(raw_message)

        logging.warning("Unknown message type: %s", message_type)
        return UnknownEvent(raw_message=raw_message, message_type=message_type)
