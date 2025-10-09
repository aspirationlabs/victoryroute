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

    @classmethod
    def from_protocol(cls, protocol_str: str) -> "Weather":
        """Parse weather from protocol string.

        Args:
            protocol_str: Weather string from protocol (e.g., "SunnyDay", "RainDance")

        Returns:
            Weather enum value

        Raises:
            ValueError: If protocol string is not recognized

        Examples:
            >>> Weather.from_protocol("SunnyDay")
            Weather.SUN
            >>> Weather.from_protocol("none")
            Weather.NONE
        """
        mapping = {
            "none": cls.NONE,
            "sun": cls.SUN,
            "sunnyday": cls.SUN,
            "rain": cls.RAIN,
            "raindance": cls.RAIN,
            "sandstorm": cls.SANDSTORM,
            "snow": cls.SNOW,
            "hail": cls.SNOW,
            "desolateland": cls.HARSH_SUN,
            "primordialsea": cls.HEAVY_RAIN,
        }
        normalized = protocol_str.lower().replace(" ", "")
        if normalized not in mapping:
            raise ValueError(f"Unknown weather protocol string: {protocol_str}")
        return mapping[normalized]


class Terrain(Enum):
    """Field terrain conditions."""

    NONE = "none"
    ELECTRIC = "electricterrain"
    GRASSY = "grassyterrain"
    PSYCHIC = "psychicterrain"
    MISTY = "mistyterrain"

    @classmethod
    def from_protocol(cls, protocol_str: str) -> "Terrain":
        """Parse terrain from protocol string.

        Args:
            protocol_str: Terrain string from protocol (e.g., "Electric Terrain", "move: grassy terrain")

        Returns:
            Terrain enum value

        Raises:
            ValueError: If protocol string is not recognized

        Examples:
            >>> Terrain.from_protocol("Electric Terrain")
            Terrain.ELECTRIC
            >>> Terrain.from_protocol("move: grassy terrain")
            Terrain.GRASSY
        """
        mapping = {
            "none": cls.NONE,
            "electricterrain": cls.ELECTRIC,
            "grassyterrain": cls.GRASSY,
            "psychicterrain": cls.PSYCHIC,
            "mistyterrain": cls.MISTY,
        }
        # Remove "move: " prefix, spaces, and normalize to lowercase
        normalized = protocol_str.lower().replace("move:", "").replace(" ", "").strip()
        if normalized not in mapping:
            raise ValueError(f"Unknown terrain protocol string: {protocol_str}")
        return mapping[normalized]


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

    @classmethod
    def from_protocol(cls, protocol_str: str) -> "SideCondition":
        """Parse side condition from protocol string.

        Args:
            protocol_str: Side condition string from protocol (e.g., "move: Stealth Rock", "Spikes")

        Returns:
            SideCondition enum value

        Raises:
            ValueError: If protocol string is not recognized

        Examples:
            >>> SideCondition.from_protocol("move: Stealth Rock")
            SideCondition.STEALTH_ROCK
            >>> SideCondition.from_protocol("Spikes")
            SideCondition.SPIKES
        """
        mapping = {
            "reflect": cls.REFLECT,
            "lightscreen": cls.LIGHT_SCREEN,
            "auroraveil": cls.AURORA_VEIL,
            "stealthrock": cls.STEALTH_ROCK,
            "spikes": cls.SPIKES,
            "toxicspikes": cls.TOXIC_SPIKES,
            "stickyweb": cls.STICKY_WEB,
            "tailwind": cls.TAILWIND,
            "safeguard": cls.SAFEGUARD,
            "mist": cls.MIST,
            "luckychant": cls.LUCKY_CHANT,
        }
        # Remove "move: " prefix, spaces, and normalize to lowercase
        normalized = protocol_str.lower().replace("move:", "").replace(" ", "").strip()
        if normalized not in mapping:
            raise ValueError(f"Unknown side condition protocol string: {protocol_str}")
        return mapping[normalized]


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
