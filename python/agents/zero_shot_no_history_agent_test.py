"""Unit tests for ZeroShotNoHistoryAgent."""

import json
import os
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai import types

from python.agents.zero_shot_no_history_agent import ZeroShotNoHistoryAgent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType
from python.game.schema.battle_state import BattleState
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


def _load_testdata_file(filename: str) -> str:
    """Load a test data file from the testdata directory.

    Args:
        filename: Name of the file to load

    Returns:
        Contents of the file
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    testdata_dir = os.path.join(current_dir, "testdata")
    filepath = os.path.join(testdata_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _parse_llm_events(llm_events_text: str) -> List[Dict[str, Any]]:
    """Parse LLM event log file into list of event dictionaries.

    Args:
        llm_events_text: Raw text from LLM events file

    Returns:
        List of parsed event dictionaries
    """
    events = []
    for line in llm_events_text.strip().split("\n"):
        if line.strip():
            events.append(json.loads(line))
    return events


def _extract_llm_response_for_turn(
    llm_events: List[Dict[str, Any]], turn: int
) -> Optional[str]:
    """Extract the final LLM response JSON for a given turn.

    Args:
        llm_events: List of LLM event dictionaries
        turn: Turn number to extract response for

    Returns:
        JSON string of the action, or None if not found
    """
    for event in llm_events:
        if event.get("action_decision") == "reasoning" and event.get("turn") == turn:
            full_action = event.get("full_action")
            if full_action:
                return json.dumps(full_action)
    return None


def _parse_request_from_showdown_events(
    showdown_events_text: str, turn: int
) -> Optional[Dict[str, Any]]:
    """Parse a request event from showdown events for a specific turn.

    Args:
        showdown_events_text: Raw showdown events text
        turn: Turn number to extract request for (0 for team preview)

    Returns:
        Parsed request dictionary, or None if not found
    """
    lines = showdown_events_text.strip().split("\n")

    if turn == 0:
        for line in lines:
            if line.startswith("|teampreview"):
                for i, next_line in enumerate(lines[lines.index(line) :]):
                    if next_line.startswith("|request|"):
                        request_json = next_line.split("|request|", 1)[1]
                        return json.loads(request_json)
        return None

    found_turn = False
    for line in lines:
        if line.startswith("|turn|") and line.strip().endswith(f"|{turn}"):
            found_turn = True
            continue

        if found_turn and line.startswith("|request|"):
            request_json = line.split("|request|", 1)[1]
            return json.loads(request_json)

    return None


def _create_battle_state_from_request(
    request_data: Dict[str, Any], our_player_id: str = "p1"
) -> BattleState:
    """Create a BattleState from a showdown request JSON.

    Args:
        request_data: Request data from showdown
        our_player_id: Our player ID

    Returns:
        BattleState constructed from the request
    """
    side = request_data.get("side", {})
    pokemon_list = side.get("pokemon", [])

    team_pokemon = []
    active_index = 0

    for i, poke_data in enumerate(pokemon_list):
        species = poke_data.get("details", "").split(",")[0]
        condition = poke_data.get("condition", "100/100")
        is_active = poke_data.get("active", False)

        if is_active:
            active_index = i

        hp_parts = condition.split("/")
        current_hp = int(hp_parts[0]) if hp_parts else 100
        max_hp = int(hp_parts[1].split()[0]) if len(hp_parts) > 1 else 100

        moves_data = poke_data.get("moves", [])
        pokemon_moves = [
            PokemonMove(name=move, current_pp=10, max_pp=10) for move in moves_data
        ]

        pokemon = PokemonState(
            species=species,
            current_hp=current_hp,
            max_hp=max_hp,
            moves=pokemon_moves,
            is_active=is_active,
            ability=poke_data.get("baseAbility", ""),
            item=poke_data.get("item", ""),
        )
        team_pokemon.append(pokemon)

    team = TeamState(pokemon=team_pokemon, active_pokemon_index=active_index)

    available_moves = []
    available_switches = []
    can_mega = False
    can_tera = False
    team_preview = request_data.get("teamPreview", False)

    if "active" in request_data and request_data["active"]:
        active_data = request_data["active"][0]
        for move_info in active_data.get("moves", []):
            if not move_info.get("disabled", False):
                available_moves.append(move_info["move"])

        can_tera_value = active_data.get("canTerastallize")
        can_tera = can_tera_value is not None and can_tera_value != ""

        can_mega_value = active_data.get("canMegaEvo")
        can_mega = can_mega_value is not None and can_mega_value != ""

    if not team_preview:
        for i, pokemon in enumerate(team_pokemon):
            if i != active_index and pokemon.current_hp > 0:
                available_switches.append(i)

    return BattleState(
        teams={"p1": team, "p2": TeamState()},
        field_state=FieldState(),
        available_moves=available_moves,
        available_switches=available_switches,
        can_mega=can_mega,
        can_tera=can_tera,
        team_preview=team_preview,
        our_player_id=our_player_id,
        player_usernames={our_player_id: "ZeroShotAgent", "p2": "Opponent"},
    )


def _make_fake_runner_sync_generator(
    response_queue: List[str], call_count_ref: List[int]
):
    """Make a synchronous generator that yields fake LLM events.

    Args:
        response_queue: List of JSON response strings
        call_count_ref: Mutable list with single element tracking call count

    Yields:
        Fake LLM events
    """
    if call_count_ref[0] < len(response_queue):
        response_text = response_queue[call_count_ref[0]]
        call_count_ref[0] += 1
    else:
        response_text = '{"action_type": "move", "move_name": "tackle"}'

    event = MagicMock()
    event.id = f"event-{call_count_ref[0]}"
    event.content = MagicMock()
    event.content.parts = [MagicMock()]
    event.content.parts[0].text = response_text
    event.actions = None
    event.invocation_id = f"invocation-{call_count_ref[0]}"
    event.author = "zero_shot_no_history_agent"
    event.error_code = None
    event.error_message = None
    event.custom_metadata = None
    event.usage_metadata = MagicMock()
    event.usage_metadata.prompt_token_count = 100
    event.usage_metadata.candidates_token_count = 50
    event.usage_metadata.total_token_count = 150

    def is_final() -> bool:
        return True

    event.is_final_response = is_final

    yield event


class FakeLlmRunner:
    """Fake LLM runner that returns predetermined responses."""

    def __init__(self, response_queue: List[str]):
        """Initialize fake runner.

        Args:
            response_queue: List of JSON response strings to return
        """
        self.response_queue = response_queue
        self.call_count_ref = [0]

    def run(
        self,
        user_id: str,
        session_id: str,
        new_message: types.Content,
    ):
        """Simulate running the LLM and yielding events.

        Args:
            user_id: User ID
            session_id: Session ID
            new_message: Message content

        Returns:
            Generator that yields fake events with predetermined responses
        """
        return _make_fake_runner_sync_generator(
            self.response_queue, self.call_count_ref
        )

    @property
    def call_count(self) -> int:
        """Get the number of times run was called."""
        return self.call_count_ref[0]


class ZeroShotNoHistoryAgentTest(unittest.IsolatedAsyncioTestCase):
    """Test ZeroShotNoHistoryAgent functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.game_data = GameData()
        self.llm_events_517 = _load_testdata_file("battle-gen9ou-517_llmevents.txt")
        self.showdown_events_517 = _load_testdata_file("battle-gen9ou-517_showdown.txt")
        self.parsed_llm_events_517 = _parse_llm_events(self.llm_events_517)

    def _setup_mocks(
        self, llm_responses: List[str]
    ) -> tuple[MagicMock, MagicMock, FakeLlmRunner]:
        """Set up mocks for Runner and SessionService.

        Args:
            llm_responses: List of JSON responses to return from fake LLM

        Returns:
            Tuple of (mock_runner_class, mock_session_service_class, fake_runner)
        """
        fake_runner = FakeLlmRunner(llm_responses)

        mock_runner_class = MagicMock()
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = fake_runner.run
        mock_runner_class.return_value = mock_runner_instance

        mock_session_service_class = MagicMock()
        mock_session_service = AsyncMock()
        mock_session = MagicMock()
        mock_session.id = "test-session-id"
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.delete_session = AsyncMock()
        mock_session_service_class.return_value = mock_session_service

        return mock_runner_class, mock_session_service_class, fake_runner

    async def test_team_preview_action(self) -> None:
        """Test that agent handles team preview correctly."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 0)
        self.assertIsNotNone(request_data, "Should find team preview request")

        state = _create_battle_state_from_request(request_data, "p1")
        self.assertTrue(state.team_preview, "Should be in team preview mode")

        llm_response = _extract_llm_response_for_turn(self.parsed_llm_events_517, 0)
        self.assertIsNotNone(llm_response, "Should find LLM response for turn 0")

        agent = ZeroShotNoHistoryAgent(model_name="test-model")
        mock_runner, mock_session_service, _ = self._setup_mocks([llm_response])

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.action_type, ActionType.TEAM_ORDER)
        self.assertEqual(action.team_order, "156243")

    async def test_move_selection(self) -> None:
        """Test that agent selects a move correctly."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 1)
        self.assertIsNotNone(request_data, "Should find request for turn 1")

        state = _create_battle_state_from_request(request_data, "p1")
        self.assertFalse(state.team_preview, "Should not be in team preview")
        self.assertGreater(len(state.available_moves), 0, "Should have available moves")

        llm_response = _extract_llm_response_for_turn(self.parsed_llm_events_517, 1)
        self.assertIsNotNone(llm_response, "Should find LLM response for turn 1")

        agent = ZeroShotNoHistoryAgent(model_name="test-model")
        mock_runner, mock_session_service, _ = self._setup_mocks([llm_response])

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_name, "Flamethrower")
        self.assertFalse(action.mega)
        self.assertFalse(action.tera)

    async def test_move_with_terastallize(self) -> None:
        """Test that agent can select a move with Terastallize."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 3)
        self.assertIsNotNone(request_data, "Should find request for turn 3")

        state = _create_battle_state_from_request(request_data, "p1")

        llm_response = _extract_llm_response_for_turn(self.parsed_llm_events_517, 3)
        self.assertIsNotNone(llm_response, "Should find LLM response for turn 3")

        agent = ZeroShotNoHistoryAgent(model_name="test-model")
        mock_runner, mock_session_service, _ = self._setup_mocks([llm_response])

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_name, "Flamethrower")
        self.assertTrue(action.tera, "Should have tera=True")

    async def test_retry_on_invalid_action(self) -> None:
        """Test that agent retries when LLM returns an invalid action."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 1)
        assert request_data is not None
        state = _create_battle_state_from_request(request_data, "p1")

        invalid_response = '{"action_type": "move", "move_name": "InvalidMove"}'
        valid_response = '{"action_type": "move", "move_name": "Flamethrower"}'

        agent = ZeroShotNoHistoryAgent(model_name="test-model", max_retries=3)
        mock_runner, mock_session_service, fake_runner = self._setup_mocks(
            [invalid_response, valid_response]
        )

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_name, "Flamethrower")
        self.assertEqual(fake_runner.call_count, 2, "Should have called LLM twice")

    async def test_validation_error_move_not_available(self) -> None:
        """Test validation error when move is not in available moves."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 1)
        assert request_data is not None
        state = _create_battle_state_from_request(request_data, "p1")

        invalid_response = '{"action_type": "move", "move_name": "Thunderbolt"}'
        valid_response = '{"action_type": "move", "move_name": "Flamethrower"}'

        agent = ZeroShotNoHistoryAgent(model_name="test-model", max_retries=3)
        mock_runner, mock_session_service, fake_runner = self._setup_mocks(
            [invalid_response, valid_response]
        )

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.move_name, "Flamethrower")
        self.assertEqual(fake_runner.call_count, 2)

    async def test_validation_error_invalid_json(self) -> None:
        """Test that agent retries on invalid JSON."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 1)
        assert request_data is not None
        state = _create_battle_state_from_request(request_data, "p1")

        invalid_json = "This is not JSON"
        valid_response = '{"action_type": "move", "move_name": "Flamethrower"}'

        agent = ZeroShotNoHistoryAgent(model_name="test-model", max_retries=3)
        mock_runner, mock_session_service, fake_runner = self._setup_mocks(
            [invalid_json, valid_response]
        )

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                action = await agent.choose_action(state, self.game_data, "test-battle")

        self.assertEqual(action.move_name, "Flamethrower")
        self.assertEqual(fake_runner.call_count, 2)

    async def test_max_retries_exceeded(self) -> None:
        """Test that agent raises error when max retries exceeded."""
        request_data = _parse_request_from_showdown_events(self.showdown_events_517, 1)
        assert request_data is not None
        state = _create_battle_state_from_request(request_data, "p1")

        invalid_response = '{"action_type": "move", "move_name": "InvalidMove"}'

        agent = ZeroShotNoHistoryAgent(model_name="test-model", max_retries=2)
        mock_runner, mock_session_service, _ = self._setup_mocks(
            [invalid_response, invalid_response, invalid_response]
        )

        with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
            with patch(
                "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                mock_session_service,
            ):
                with self.assertRaises(ValueError) as context:
                    await agent.choose_action(state, self.game_data, "test-battle")

        self.assertIn("Failed to get valid action", str(context.exception))

    async def test_multiple_turns_sequence(self) -> None:
        """Test agent across multiple sequential turns."""
        agent = ZeroShotNoHistoryAgent(model_name="test-model")

        turns_to_test = [0, 1, 2]
        for turn in turns_to_test:
            request_data = _parse_request_from_showdown_events(
                self.showdown_events_517, turn
            )
            if request_data is None:
                continue

            state = _create_battle_state_from_request(request_data, "p1")
            llm_response = _extract_llm_response_for_turn(
                self.parsed_llm_events_517, turn
            )

            if llm_response is None:
                continue

            mock_runner, mock_session_service, _ = self._setup_mocks([llm_response])

            with patch("python.agents.zero_shot_no_history_agent.Runner", mock_runner):
                with patch(
                    "python.agents.zero_shot_no_history_agent.InMemorySessionService",
                    mock_session_service,
                ):
                    action = await agent.choose_action(
                        state, self.game_data, "test-battle"
                    )

            self.assertIsNotNone(action, f"Turn {turn} should return an action")

            if turn == 0:
                self.assertEqual(action.action_type, ActionType.TEAM_ORDER)
            else:
                self.assertEqual(action.action_type, ActionType.MOVE)


if __name__ == "__main__":
    unittest.main()
