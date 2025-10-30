from __future__ import annotations

import json
import re
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    Generic,
)
from typing import get_args, get_origin

from absl import logging
from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.genai import types
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

JsonType = Union[dict, list, str, int, float, bool, None]
ModelT = TypeVar("ModelT", bound=BaseModel)


class JsonLlmAgent(SequentialAgent, Generic[ModelT]):
    """Wraps an agent with an additional coercion step that guarantees JSON output."""

    def __init__(
        self,
        *,
        base_agent: BaseAgent,
        output_schema: Type[ModelT],
        data_input_key: str,
        json_output_key: str,
        model: Union[str, BaseLlm],
    ) -> None:
        if not isinstance(base_agent, BaseAgent):
            raise TypeError("JsonLlmAgent requires a BaseAgent to wrap.")
        coercion_agent_name = f"{base_agent.name}_json_coercion"

        coercion_agent = self._build_coercion_agent(
            coercion_agent_name,
            model,
            output_schema,
            data_input_key,
            json_output_key,
        )

        super().__init__(
            name=f"{base_agent.name}_json_adapter",
            sub_agents=[base_agent, coercion_agent],
        )
        self._data_input_key = data_input_key
        self._json_output_key = json_output_key
        self._coercion_agent_name = coercion_agent_name
        self._output_schema = output_schema

    def _build_coercion_agent(
        self, agent_name, model, output_schema, data_input_key, json_output_key
    ) -> LlmAgent:
        structure_lines: List[str] = []
        example_payload: Dict[str, Any] = {}

        for field_name, field in output_schema.model_fields.items():
            structure_lines.append(self._format_structure_line(field_name, field))
            example_payload[field_name] = self._example_value_for_field(field)

        structure_section = "\n".join(structure_lines)
        example_json = (
            json.dumps(example_payload, indent=2, ensure_ascii=False)
            .replace("{", "{{")
            .replace("}", "}}")
        )

        draft_placeholder = "{" + data_input_key + "}"
        coercion_instruction = (
            "You are a structured-output formatter. Read the draft value provided below "
            "and rewrite it as clean JSON that exactly matches the schema. "
            "The draft may be formatted as markdown sections with JSON keys in parentheses. "
            "For example:\n"
            "## Section Name (json_key)\n"
            "value content\n\n"
            "Extract the json_key from parentheses and use the content below it as the value. "
            "For lists with bullet points, extract each item. For items with metadata like "
            "'(confidence: 0.8)', preserve that structure in the list objects.\n\n"
            "Respond only with the final JSON object—do not include explanations, "
            "surrounding text, or code fences.\n\n"
            "# Draft\n"
            f"{draft_placeholder}\n\n"
            "## Output Structure\n"
            f"{structure_section}\n\n"
            "## Example Output\n"
            f"```json\n{example_json}\n```"
        )

        return LlmAgent(
            name=agent_name,
            model=model,
            instruction=coercion_instruction,
            include_contents="none",
            output_schema=output_schema,
            output_key=json_output_key,
            after_model_callback=self._build_after_model_callback(),
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

    @staticmethod
    def _format_structure_line(field_name: str, field: FieldInfo) -> str:
        type_repr = JsonLlmAgent._describe_annotation(field.annotation)
        description = field.description or "No description provided."
        return f"- {field_name} ({type_repr}): {description}"

    @staticmethod
    def _describe_annotation(annotation: Any) -> str:
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            non_none = [arg for arg in args if arg is not type(None)]
            if len(non_none) == 1 and len(non_none) + 1 == len(args):
                return f"Optional[{JsonLlmAgent._describe_annotation(non_none[0])}]"
            return (
                "Union["
                + ", ".join(JsonLlmAgent._describe_annotation(arg) for arg in args)
                + "]"
            )
        if origin in (list, List):
            elem_args = get_args(annotation)
            elem_desc = (
                JsonLlmAgent._describe_annotation(elem_args[0]) if elem_args else "Any"
            )
            return f"List[{elem_desc}]"
        if origin in (dict, Dict):
            key_args = get_args(annotation)
            if len(key_args) == 2:
                key_desc = JsonLlmAgent._describe_annotation(key_args[0])
                val_desc = JsonLlmAgent._describe_annotation(key_args[1])
                return f"Dict[{key_desc}, {val_desc}]"
            return "Dict"
        if isinstance(annotation, type):
            return getattr(annotation, "__name__", str(annotation))
        return str(annotation)

    @staticmethod
    def _example_value_for_field(field: FieldInfo) -> Any:
        if field.default is not PydanticUndefined:
            return field.default
        if field.default_factory is not None and callable(field.default_factory):
            return field.default_factory()
        return JsonLlmAgent._example_value_for_annotation(field.annotation)

    @staticmethod
    def _example_value_for_annotation(annotation: Any) -> Any:
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if args:
                return JsonLlmAgent._example_value_for_annotation(args[0])
            return None
        if annotation in (str,):
            return ""
        if annotation in (bool,):
            return False
        if annotation in (int,):
            return 0
        if annotation in (float,):
            return 0.0
        if origin in (list, List):
            return []
        if origin in (dict, Dict):
            return {}
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return {}
        return None

    def _build_after_model_callback(
        self,
    ) -> Callable[[CallbackContext, LlmResponse], Optional[LlmResponse]]:
        def _after_model_callback(
            callback_context: CallbackContext, llm_response: LlmResponse
        ) -> Optional[LlmResponse]:
            return self._clean_model_output(llm_response)

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
                self._coercion_agent_name,
                raw_text,
            )
            return None

        try:
            model_data = self._output_schema.model_validate(structured)
        except ValidationError as e:
            logging.warning(
                "[%s] Extracted JSON failed schema validation: %s",
                self._coercion_agent_name,
                e,
            )
            return None

        clean_json = model_data.model_dump_json()
        if clean_json == raw_text.strip():
            return None

        logging.info(
            "[%s] Cleaned model output from %d to %d characters: %s",
            self._coercion_agent_name,
            len(raw_text),
            len(clean_json),
            clean_json,
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
