"""Enums for battle state representation."""

from enum import Enum


class Status(Enum):
    """Pokemon status conditions."""

    NONE = "none"
    BURN = "brn"
    PARALYSIS = "par"
    POISON = "psn"
    TOXIC = "tox"
    SLEEP = "slp"
    FREEZE = "frz"


class Weather(Enum):
    """Field weather conditions."""

    NONE = "none"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    SNOW = "snow"
    HARSH_SUN = "desolateland"
    HEAVY_RAIN = "primordialsea"


class Terrain(Enum):
    """Field terrain conditions."""

    NONE = "none"
    ELECTRIC = "electricterrain"
    GRASSY = "grassyterrain"
    PSYCHIC = "psychicterrain"
    MISTY = "mistyterrain"


class SideCondition(Enum):
    """Side-specific field conditions."""

    REFLECT = "reflect"
    LIGHT_SCREEN = "lightscreen"
    AURORA_VEIL = "auroraveil"
    STEALTH_ROCK = "stealthrock"
    SPIKES = "spikes"
    TOXIC_SPIKES = "toxicspikes"
    STICKY_WEB = "stickyweb"
    TAILWIND = "tailwind"
    SAFEGUARD = "safeguard"
    MIST = "mist"
    LUCKY_CHANT = "luckychant"


class FieldEffect(Enum):
    """Global field effects."""

    TRICK_ROOM = "trickroom"
    MAGIC_ROOM = "magicroom"
    WONDER_ROOM = "wonderroom"
    GRAVITY = "gravity"
    MUD_SPORT = "mudsport"
    WATER_SPORT = "watersport"


class Stat(Enum):
    """Pokemon stats."""

    HP = "hp"
    ATK = "atk"
    DEF = "def"
    SPA = "spa"
    SPD = "spd"
    SPE = "spe"
    ACCURACY = "accuracy"
    EVASION = "evasion"


class VolatileCondition(Enum):
    """Temporary pokemon conditions that reset on switch."""

    SUBSTITUTE = "substitute"
    PROTECT = "protect"
    CONFUSION = "confusion"
    FLINCH = "flinch"
    TAUNT = "taunt"
    ENCORE = "encore"
    TORMENT = "torment"
    DISABLE = "disable"
    YAWN = "yawn"
    HEAL_BLOCK = "healblock"
    EMBARGO = "embargo"
    LEECH_SEED = "leechseed"
    PERISH_SONG = "perishsong"
    INGRAIN = "ingrain"
    AQUA_RING = "aquaring"
    MAGNET_RISE = "magnetrise"
    TELEKINESIS = "telekinesis"
