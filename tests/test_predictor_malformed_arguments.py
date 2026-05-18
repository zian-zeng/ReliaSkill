import unittest

from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.predictor import LocalHFPredictorBackend, OpenAICompatiblePredictorBackend


class _FakeRunner:
    def __init__(self, content: str) -> None:
        self.content = content

    def generate_chat(self, *_args, **_kwargs) -> str:
        return self.content


class _FakeOpenAIBackend(OpenAICompatiblePredictorBackend):
    def __init__(self, content: str) -> None:
        super().__init__(api_url="https://example.invalid", model="fake")
        self.content = content

    def _post_json(self, _payload):
        return {"choices": [{"message": {"content": self.content}}]}


def _tool() -> ToolIR:
    return ToolIR(
        tool_name="search",
        tool_purpose="Search documents.",
        arguments=[ArgumentIR(name="query", type="string", required=True)],
    )


def _skill() -> GeneratedSkill:
    return GeneratedSkill(baseline_name="generated_skill_base", skill_summary="Search documents.")


def _task() -> EvalTask:
    return EvalTask(task_id="t1", tool_name="search", user_request="Search for notes", expected_arguments={"query": "notes"})


class MalformedArgumentPredictionTests(unittest.TestCase):
    def test_local_hf_non_object_arguments_become_invalid_prediction_not_exception(self) -> None:
        backend = LocalHFPredictorBackend(model_name_or_path="fake")
        backend.runner = _FakeRunner('{"should_call": true, "arguments": ["query", "notes", "extra"]}')

        prediction = backend.predict(_tool(), _skill(), _task())

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertIn("argument_parse_error", prediction.metadata)
        self.assertIn("list", prediction.metadata["argument_parse_error"])

    def test_openai_compatible_non_object_arguments_become_invalid_prediction_not_exception(self) -> None:
        backend = _FakeOpenAIBackend('{"should_call": true, "arguments": ["query", "notes", "extra"]}')

        prediction = backend.predict(_tool(), _skill(), _task())

        self.assertTrue(prediction.should_call)
        self.assertEqual(prediction.predicted_arguments, {})
        self.assertIn("argument_parse_error", prediction.metadata)


if __name__ == "__main__":
    unittest.main()
