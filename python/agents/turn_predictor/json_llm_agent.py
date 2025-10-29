from __future__ import annotations

import json
import re
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    Generic,
)

from absl import logging
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from pydantic import BaseModel, ValidationError

JsonType = Union[dict, list, str, int, float, bool, None]
ModelT = TypeVar("ModelT", bound=BaseModel)
_VALIDATION_TOOL_NAME = "validate_json_candidate"


class JsonLlmAgent(LlmAgent, Generic[ModelT]):
    """LLM agent wrapper that enforces JSON responses for a pydantic schema."""

    def __init__(
        self,
        *,
        model: LiteLlm,
        name: str,
        instruction: str,
        output_schema: Type[ModelT],
        tools: Optional[Sequence[Callable[..., Any]]] = None,
        after_model_callback: Optional[
            Callable[[CallbackContext, LlmResponse], Optional[LlmResponse]]
        ] = None,
        instruction_validation_suffix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the agent with JSON cleaning and validation support.

        Args:
            model: LiteLlm instance to use for generation.
            name: Agent name.
            instruction: Base system instruction.
            output_schema: Pydantic model class that describes the desired response.
            tools: Optional sequence of tools to expose to the model.
            after_model_callback: Optional extra callback to run after JSON cleaning.
            instruction_validation_suffix: Optional override for the appended validation
                blurb. When None, the default message is used.
            **kwargs: Forwarded to LlmAgent.
        """
        if not isinstance(model, LiteLlm):
            raise TypeError("JsonLlmAgent requires a LiteLlm model instance.")

        validation_tool = self._build_validation_tool()
        combined_tools: List[Callable[..., Any]] = list(tools or [])
        combined_tools.append(validation_tool)

        validation_suffix = instruction_validation_suffix or (
            "When drafting your final response, remember that it must be valid JSON "
            f"that matches the required schema. Use the `{_VALIDATION_TOOL_NAME}` tool "
            "to confirm your draft parses correctly before responding. Only return "
            "the final JSON object—do not include explanations or code fences."
        )

        augmented_instruction = f"{instruction.rstrip()}\n\n{validation_suffix}"

        super().__init__(
            model=model,
            name=name,
            instruction=augmented_instruction,
            tools=combined_tools,
            after_model_callback=self._build_after_model_callback(),
            output_schema=output_schema,
            **kwargs,
        )
        self._output_schema: Type[ModelT] = output_schema
        self._agent_name = name
        self._user_after_model_callback: Optional[
            Callable[[CallbackContext, LlmResponse], Optional[LlmResponse]]
        ] = after_model_callback

    def _build_validation_tool(self) -> Callable[[str], str]:
        def validate_json_candidate(candidate: str) -> str:
            """Validate whether the provided JSON string conforms to the expected schema."""
            try:
                structured_payload = self._model_validate_candidate(candidate)
            except ValidationError as exc:
                logging.debug(
                    "[%s] Validation tool rejected candidate JSON: %s",
                    self._agent_name,
                    exc,
                )
                return "false"

            if structured_payload is None:
                logging.debug(
                    "[%s] Validation tool could not extract JSON from candidate.",
                    self._agent_name,
                )
                return "false"

            return "true"

        return validate_json_candidate

    def _build_after_model_callback(
        self,
    ) -> Callable[[CallbackContext, LlmResponse], Optional[LlmResponse]]:
        def _after_model_callback(
            callback_context: CallbackContext,
            llm_response: LlmResponse,
        ) -> Optional[LlmResponse]:
            cleaned_response = self._clean_model_output(llm_response)

            response_for_user_callback = cleaned_response or llm_response
            user_result: Optional[LlmResponse] = None
            if self._user_after_model_callback:
                user_result = self._user_after_model_callback(
                    callback_context, response_for_user_callback
                )

            if user_result is not None:
                return user_result

            return cleaned_response

        return _after_model_callback

    def _clean_model_output(self, llm_response: LlmResponse) -> Optional[LlmResponse]:
        if not llm_response or not llm_response.content:
            return None

        parts: Iterable[types.Part] = getattr(llm_response.content, "parts", [])
        first_part: Optional[types.Part] = next(iter(parts), None)
        if first_part is None or not first_part.text:
            return None

        raw_text = first_part.text or ""
        structured = self._extract_json_from_text(raw_text)
        if structured is None:
            logging.warning(
                "[%s] Could not extract JSON from model output: %s",
                self._agent_name,
                raw_text,
            )
            return None

        try:
            model_data = self._output_schema.model_validate(structured)
        except ValidationError as e:
            logging.warning(
                "[%s] Extracted JSON failed schema validation: %s",
                self._agent_name,
                e,
            )
            return None

        clean_json = model_data.model_dump_json()
        if clean_json == raw_text.strip():
            return None

        logging.info(
            "[%s] Cleaned model output from %d to %d characters",
            self._agent_name,
            len(raw_text),
            len(clean_json),
        )

        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=clean_json)],
                role=llm_response.content.role,
            ),
            grounding_metadata=llm_response.grounding_metadata,
        )

    def _model_validate_candidate(self, candidate: str) -> Optional[ModelT]:
        if not candidate or not isinstance(candidate, str):
            return None

        structured = self._extract_json_from_text(candidate)
        if structured is None:
            return None

        return self._output_schema.model_validate(structured)

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[JsonType]:
        if not text:
            return None

        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        markdown_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
        for match in markdown_matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        brace_result = JsonLlmAgent._extract_json_by_delimiters(text, "{", "}")
        if brace_result is not None:
            return brace_result

        return JsonLlmAgent._extract_json_by_delimiters(text, "[", "]")

    @staticmethod
    def _extract_json_by_delimiters(
        text: str, opener: str, closer: str
    ) -> Optional[JsonType]:
        stack: List[str] = []
        start_idx: Optional[int] = None

        for idx, char in enumerate(text):
            if char == opener:
                if start_idx is None:
                    start_idx = idx
                stack.append(char)
            elif char == closer and stack:
                stack.pop()
                if not stack and start_idx is not None:
                    candidate = text[start_idx : idx + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        start_idx = None

        return None
