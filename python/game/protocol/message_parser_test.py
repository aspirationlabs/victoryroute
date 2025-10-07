from typing import Optional

from absl.testing import absltest, parameterized

from python.game.events.battle_event import (
    BoostEvent,
    ClearPokeEvent,
    CritEvent,
    DamageEvent,
    FaintEvent,
    GenEvent,
    HealEvent,
    HitCountEvent,
    ImmuneEvent,
    MissEvent,
    MoveEvent,
    PlayerEvent,
    PokeEvent,
    RequestEvent,
    ResistedEvent,
    StatusEvent,
    SuperEffectiveEvent,
    SwitchEvent,
    TeamPreviewEvent,
    TeamSizeEvent,
    TierEvent,
    TurnEvent,
    UnboostEvent,
    UpkeepEvent,
)
from python.game.protocol.message_parser import MessageParser


class MessageParserTest(parameterized.TestCase):
    @parameterized.parameters(
        ("|turn|1", 1),
        ("|turn|2", 2),
        ("|turn|10", 10),
        ("|turn|25", 25),
    )
    def test_parse_turn(self, raw_message: str, expected_turn: int) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, TurnEvent)
        self.assertEqual(event.turn_number, expected_turn)

    @parameterized.parameters(
        ("|gen|9", 9),
        ("|gen|1", 1),
        ("|gen|8", 8),
    )
    def test_parse_gen(self, raw_message: str, expected_gen: int) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, GenEvent)
        self.assertEqual(event.generation, expected_gen)

    @parameterized.parameters(
        ("|tier|[gen 9] ou", "[gen 9] ou"),
        ("|tier|[gen 9] ubers", "[gen 9] ubers"),
    )
    def test_parse_tier(self, raw_message: str, expected_tier: str) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, TierEvent)
        self.assertEqual(event.tier, expected_tier)

    @parameterized.parameters(
        ("|player|p1|qways|169|1659", "p1", "qways", "169", 1659),
        ("|player|p2|how play pkm|yellow|1630", "p2", "how play pkm", "yellow", 1630),
        ("|player|p1|zachados|rood|1668", "p1", "zachados", "rood", 1668),
    )
    def test_parse_player(
        self,
        raw_message: str,
        expected_player_id: str,
        expected_username: str,
        expected_avatar: str,
        expected_rating: int,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, PlayerEvent)
        self.assertEqual(event.player_id, expected_player_id)
        self.assertEqual(event.username, expected_username)
        self.assertEqual(event.avatar, expected_avatar)
        self.assertEqual(event.rating, expected_rating)

    @parameterized.parameters(
        ("|teamsize|p1|6", "p1", 6),
        ("|teamsize|p2|6", "p2", 6),
    )
    def test_parse_teamsize(
        self, raw_message: str, expected_player: str, expected_size: int
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, TeamSizeEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.size, expected_size)

    @parameterized.parameters(
        (
            "|switch|p1a: raging bolt|raging bolt|100/100",
            "p1",
            "a",
            "raging bolt",
            "raging bolt",
            100,
            100,
            None,
            None,
        ),
        (
            "|switch|p2a: kommo-o|kommo-o, f|100/100",
            "p2",
            "a",
            "kommo-o",
            "kommo-o",
            100,
            100,
            "f",
            None,
        ),
        (
            "|switch|p1a: landorus|landorus-therian, m|100/100",
            "p1",
            "a",
            "landorus",
            "landorus-therian",
            100,
            100,
            "m",
            None,
        ),
        (
            "|switch|p2a: rotom|rotom-wash|100/100",
            "p2",
            "a",
            "rotom",
            "rotom-wash",
            100,
            100,
            None,
            None,
        ),
        (
            "|switch|p2a: rotom|rotom-wash|84/100",
            "p2",
            "a",
            "rotom",
            "rotom-wash",
            84,
            100,
            None,
            None,
        ),
        (
            "|switch|p2a: gholdengo|gholdengo|56/100",
            "p2",
            "a",
            "gholdengo",
            "gholdengo",
            56,
            100,
            None,
            None,
        ),
        (
            "|switch|p1a: ogerpon|ogerpon-wellspring, f|100/100",
            "p1",
            "a",
            "ogerpon",
            "ogerpon-wellspring",
            100,
            100,
            "f",
            None,
        ),
        (
            "|switch|p2a: dragonite|dragonite, f|100/100",
            "p2",
            "a",
            "dragonite",
            "dragonite",
            100,
            100,
            "f",
            None,
        ),
        (
            "|switch|p1a: landorus|landorus-therian, m|41/100",
            "p1",
            "a",
            "landorus",
            "landorus-therian",
            41,
            100,
            "m",
            None,
        ),
        (
            "|switch|p1a: iron moth|iron moth|100/100",
            "p1",
            "a",
            "iron moth",
            "iron moth",
            100,
            100,
            None,
            None,
        ),
        (
            "|switch|p1a: zamazenta|zamazenta|100/100",
            "p1",
            "a",
            "zamazenta",
            "zamazenta",
            100,
            100,
            None,
            None,
        ),
        (
            "|switch|p1a: iron crown|iron crown|52/100",
            "p1",
            "a",
            "iron crown",
            "iron crown",
            52,
            100,
            None,
            None,
        ),
        (
            "|switch|p1a: ogerpon|ogerpon-wellspring, f|47/100",
            "p1",
            "a",
            "ogerpon",
            "ogerpon-wellspring",
            47,
            100,
            "f",
            None,
        ),
        (
            "|switch|p1a: glisca|gliscor, m|100/100",
            "p1",
            "a",
            "glisca",
            "gliscor",
            100,
            100,
            "m",
            None,
        ),
        (
            "|switch|p2a: glimmora|glimmora, m|100/100",
            "p2",
            "a",
            "glimmora",
            "glimmora",
            100,
            100,
            "m",
            None,
        ),
    )
    def test_parse_switch(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_species: str,
        expected_hp_current: int,
        expected_hp_max: int,
        expected_gender: str | None,
        expected_status: str | None,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, SwitchEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.species, expected_species)
        self.assertEqual(event.hp_current, expected_hp_current)
        self.assertEqual(event.hp_max, expected_hp_max)
        self.assertEqual(event.gender, expected_gender)
        self.assertEqual(event.status, expected_status)

    @parameterized.parameters(
        ("|-damage|p2a: gholdengo|81/100", "p2", "a", "gholdengo", 81, 100, None, None),
        ("|-damage|p2a: gholdengo|56/100", "p2", "a", "gholdengo", 56, 100, None, None),
        (
            "|-damage|p1a: landorus|88/100|[from] stealth rock",
            "p1",
            "a",
            "landorus",
            88,
            100,
            None,
            " stealth rock",
        ),
        ("|-damage|p1a: landorus|41/100", "p1", "a", "landorus", 41, 100, None, None),
        ("|-damage|p2a: rotom|78/100", "p2", "a", "rotom", 78, 100, None, None),
        (
            "|-damage|p1a: raging bolt|81/100",
            "p1",
            "a",
            "raging bolt",
            81,
            100,
            None,
            None,
        ),
        (
            "|-damage|p1a: raging bolt|75/100",
            "p1",
            "a",
            "raging bolt",
            75,
            100,
            None,
            None,
        ),
        ("|-damage|p2a: enamorus|76/100", "p2", "a", "enamorus", 76, 100, None, None),
        (
            "|-damage|p1a: iron crown|94/100|[from] stealth rock",
            "p1",
            "a",
            "iron crown",
            94,
            100,
            None,
            " stealth rock",
        ),
        (
            "|-damage|p1a: iron crown|76/100",
            "p1",
            "a",
            "iron crown",
            76,
            100,
            None,
            None,
        ),
        (
            "|-damage|p2a: rotom|72/100|[from] stealth rock",
            "p2",
            "a",
            "rotom",
            72,
            100,
            None,
            " stealth rock",
        ),
        ("|-damage|p2a: rotom|65/100", "p2", "a", "rotom", 65, 100, None, None),
        ("|-damage|p1a: landorus|0 fnt", "p1", "a", "landorus", 0, 100, None, None),
        (
            "|-damage|p2a: dragonite|84/100|[from] item: rocky helmet|[of] p1a: landorus",
            "p2",
            "a",
            "dragonite",
            84,
            100,
            None,
            " item: rocky helmet",
        ),
        ("|-damage|p1a: iron moth|0 fnt", "p1", "a", "iron moth", 0, 100, None, None),
    )
    def test_parse_damage(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_hp_current: int,
        expected_hp_max: int,
        expected_status: str | None,
        expected_source: str | None,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, DamageEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.hp_current, expected_hp_current)
        self.assertEqual(event.hp_max, expected_hp_max)
        self.assertEqual(event.status, expected_status)
        self.assertEqual(event.source, expected_source)

    @parameterized.parameters(
        (
            "|-heal|p2a: rotom|84/100|[from] item: leftovers",
            "p2",
            "a",
            "rotom",
            84,
            100,
            " item: leftovers",
        ),
        (
            "|-heal|p1a: zamazenta|37/100|[from] item: leftovers",
            "p1",
            "a",
            "zamazenta",
            37,
            100,
            " item: leftovers",
        ),
        (
            "|-heal|p2a: gholdengo|56/100|[from] item: leftovers",
            "p2",
            "a",
            "gholdengo",
            56,
            100,
            " item: leftovers",
        ),
        (
            "|-heal|p2a: rotom|65/100|[from] item: leftovers",
            "p2",
            "a",
            "rotom",
            65,
            100,
            " item: leftovers",
        ),
        (
            "|-heal|p1a: zamazenta|43/100|[from] item: leftovers",
            "p1",
            "a",
            "zamazenta",
            43,
            100,
            " item: leftovers",
        ),
        (
            "|-heal|p2a: kingambit|74/100|[from] item: leftovers",
            "p2",
            "a",
            "kingambit",
            74,
            100,
            " item: leftovers",
        ),
    )
    def test_parse_heal(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_hp_current: int,
        expected_hp_max: int,
        expected_source: str | None,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, HealEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.hp_current, expected_hp_current)
        self.assertEqual(event.hp_max, expected_hp_max)
        self.assertEqual(event.source, expected_source)

    @parameterized.parameters(
        ("|faint|p2a: kommo-o", "p2", "a", "kommo-o"),
        ("|faint|p1a: landorus", "p1", "a", "landorus"),
        ("|faint|p1a: iron moth", "p1", "a", "iron moth"),
        ("|faint|p2a: dragonite", "p2", "a", "dragonite"),
        ("|faint|p2a: gholdengo", "p2", "a", "gholdengo"),
        ("|faint|p2a: rotom", "p2", "a", "rotom"),
    )
    def test_parse_faint(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, FaintEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-status|p1a: raging bolt|brn", "p1", "a", "raging bolt", "brn"),
        ("|-status|p1a: glisca|tox|[from] item: toxic orb", "p1", "a", "glisca", "tox"),
    )
    def test_parse_status(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_status: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, StatusEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.status, expected_status)

    @parameterized.parameters(
        (
            "|move|p2a: kommo-o|stealth rock|p1a: iron crown",
            "p2",
            "a",
            "kommo-o",
            "stealth rock",
            "p1",
            "a",
            "iron crown",
        ),
        (
            "|move|p1a: iron crown|psychic noise|p2a: gholdengo",
            "p1",
            "a",
            "iron crown",
            "psychic noise",
            "p2",
            "a",
            "gholdengo",
        ),
        (
            "|move|p1a: iron crown|volt switch|p2a: gholdengo",
            "p1",
            "a",
            "iron crown",
            "volt switch",
            "p2",
            "a",
            "gholdengo",
        ),
        (
            "|move|p2a: gholdengo|shadow ball|p1a: landorus",
            "p2",
            "a",
            "gholdengo",
            "shadow ball",
            "p1",
            "a",
            "landorus",
        ),
        (
            "|move|p1a: landorus|stealth rock|p2a: rotom",
            "p1",
            "a",
            "landorus",
            "stealth rock",
            "p2",
            "a",
            "rotom",
        ),
        (
            "|move|p1a: landorus|u-turn|p2a: rotom",
            "p1",
            "a",
            "landorus",
            "u-turn",
            "p2",
            "a",
            "rotom",
        ),
        (
            "|move|p2a: rotom|hydro pump|p1a: raging bolt",
            "p2",
            "a",
            "rotom",
            "hydro pump",
            "p1",
            "a",
            "raging bolt",
        ),
        (
            "|move|p2a: rotom|volt switch|p1a: raging bolt",
            "p2",
            "a",
            "rotom",
            "volt switch",
            "p1",
            "a",
            "raging bolt",
        ),
        (
            "|move|p1a: raging bolt|dragon pulse|p2a: enamorus",
            "p1",
            "a",
            "raging bolt",
            "dragon pulse",
            "p2",
            "a",
            "enamorus",
        ),
        (
            "|move|p2a: enamorus|moonblast|p1a: iron crown",
            "p2",
            "a",
            "enamorus",
            "moonblast",
            "p1",
            "a",
            "iron crown",
        ),
        (
            "|move|p1a: iron crown|tachyon cutter|p2a: rotom",
            "p1",
            "a",
            "iron crown",
            "tachyon cutter",
            "p2",
            "a",
            "rotom",
        ),
        (
            "|move|p1a: iron crown|future sight|p2a: rotom",
            "p1",
            "a",
            "iron crown",
            "future sight",
            "p2",
            "a",
            "rotom",
        ),
        (
            "|move|p2a: rotom|volt switch|p1a: iron crown",
            "p2",
            "a",
            "rotom",
            "volt switch",
            "p1",
            "a",
            "iron crown",
        ),
        (
            "|move|p2a: enamorus|substitute|p2a: enamorus",
            "p2",
            "a",
            "enamorus",
            "substitute",
            "p2",
            "a",
            "enamorus",
        ),
        (
            "|move|p2a: dragonite|dragon dance|p2a: dragonite",
            "p2",
            "a",
            "dragonite",
            "dragon dance",
            "p2",
            "a",
            "dragonite",
        ),
    )
    def test_parse_move(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_move: str,
        expected_target_player: str | None,
        expected_target_position: str | None,
        expected_target_name: str | None,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, MoveEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.move_name, expected_move)
        self.assertEqual(event.target_player, expected_target_player)
        self.assertEqual(event.target_position, expected_target_position)
        self.assertEqual(event.target_name, expected_target_name)

    @parameterized.parameters(
        ("|-boost|p2a: dragonite|atk|1", "p2", "a", "dragonite", "atk", 1),
        ("|-boost|p2a: dragonite|spe|1", "p2", "a", "dragonite", "spe", 1),
        ("|-boost|p1a: zamazenta|def|1", "p1", "a", "zamazenta", "def", 1),
        ("|-boost|p1a: zamazenta|def|2", "p1", "a", "zamazenta", "def", 2),
        ("|-boost|p2a: enamorus|atk|1", "p2", "a", "enamorus", "atk", 1),
        ("|-boost|p2a: enamorus|def|1", "p2", "a", "enamorus", "def", 1),
    )
    def test_parse_boost(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_stat: str,
        expected_amount: int,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, BoostEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.stat, expected_stat)
        self.assertEqual(event.amount, expected_amount)

    @parameterized.parameters(
        ("|-unboost|p2a: gholdengo|atk|1", "p2", "a", "gholdengo", "atk", 1),
        ("|-unboost|p1a: ogerpon|spd|1", "p1", "a", "ogerpon", "spd", 1),
        ("|-unboost|p2a: dragonite|atk|1", "p2", "a", "dragonite", "atk", 1),
    )
    def test_parse_unboost(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_stat: str,
        expected_amount: int,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, UnboostEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.stat, expected_stat)
        self.assertEqual(event.amount, expected_amount)

    @parameterized.parameters(
        ("|-supereffective|p2a: kommo-o", "p2", "a", "kommo-o"),
        ("|-supereffective|p1a: landorus", "p1", "a", "landorus"),
        ("|-supereffective|p2a: dragonite", "p2", "a", "dragonite"),
    )
    def test_parse_supereffective(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, SuperEffectiveEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-resisted|p2a: gholdengo", "p2", "a", "gholdengo"),
        ("|-resisted|p1a: raging bolt", "p1", "a", "raging bolt"),
        ("|-resisted|p2a: rotom", "p2", "a", "rotom"),
    )
    def test_parse_resisted(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, ResistedEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-immune|p2a: enamorus", "p2", "a", "enamorus"),
        ("|-immune|p1a: corviknight", "p1", "a", "corviknight"),
        ("|-immune|p1a: dragapult", "p1", "a", "dragapult"),
    )
    def test_parse_immune(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, ImmuneEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-crit|p1a: zamazenta", "p1", "a", "zamazenta"),
        ("|-crit|p1a: darkrai", "p1", "a", "darkrai"),
        ("|-crit|p1a: iron treads", "p1", "a", "iron treads"),
    )
    def test_parse_crit(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, CritEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-miss|p2a: kyurem|p1a: heatran", "p2", "a", "kyurem"),
        ("|-miss|p1a: heatran|p2a: cinderace", "p1", "a", "heatran"),
    )
    def test_parse_miss(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, MissEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)

    @parameterized.parameters(
        ("|-hitcount|p2a: rotom|2", "p2", "a", "rotom", 2),
        ("|-hitcount|p1a: heatran|5", "p1", "a", "heatran", 5),
        ("|-hitcount|p1a: dondozo|4", "p1", "a", "dondozo", 4),
    )
    def test_parse_hitcount(
        self,
        raw_message: str,
        expected_player: str,
        expected_position: str,
        expected_name: str,
        expected_count: int,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, HitCountEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.position, expected_position)
        self.assertEqual(event.pokemon_name, expected_name)
        self.assertEqual(event.count, expected_count)

    @parameterized.parameters(
        ("|poke|p1|landorus-therian, m|", "p1", "landorus-therian", "m", False),
        ("|poke|p1|ogerpon-wellspring, f|", "p1", "ogerpon-wellspring", "f", False),
        ("|poke|p1|raging bolt|", "p1", "raging bolt", None, False),
    )
    def test_parse_poke(
        self,
        raw_message: str,
        expected_player: str,
        expected_species: str,
        expected_gender: Optional[str],
        expected_shiny: bool,
    ) -> None:
        parser = MessageParser()
        event = parser.parse(raw_message)
        self.assertIsInstance(event, PokeEvent)
        self.assertEqual(event.player_id, expected_player)
        self.assertEqual(event.species, expected_species)
        self.assertEqual(event.gender, expected_gender)
        self.assertEqual(event.shiny, expected_shiny)

    def test_parse_clearpoke(self) -> None:
        parser = MessageParser()
        event = parser.parse("|clearpoke")
        self.assertIsInstance(event, ClearPokeEvent)

    def test_parse_teampreview(self) -> None:
        parser = MessageParser()
        event = parser.parse("|teampreview")
        self.assertIsInstance(event, TeamPreviewEvent)

    def test_parse_upkeep(self) -> None:
        parser = MessageParser()
        event = parser.parse("|upkeep")
        self.assertIsInstance(event, UpkeepEvent)

    def test_parse_request(self) -> None:
        parser = MessageParser()
        request_json = '{"active":[{"moves":[{"move":"Thunderbolt"}]}]}'
        event = parser.parse(f"|request|{request_json}")
        self.assertIsInstance(event, RequestEvent)
        self.assertEqual(event.request_json, request_json)


if __name__ == "__main__":
    absltest.main()
