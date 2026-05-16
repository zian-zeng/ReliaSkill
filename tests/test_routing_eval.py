import unittest

from autoskill.eval_types import EvalTask
from autoskill.ir import ArgumentIR, GeneratedSkill, ToolIR
from autoskill.retrieval_runtime import retrieve_candidate_tools
from autoskill.routing_eval import select_tool_for_task


def _path_tool(name: str, purpose: str) -> ToolIR:
    return ToolIR(
        tool_name=name,
        tool_purpose=purpose,
        arguments=[ArgumentIR(name="path", type="string", required=True, description="Directory path")],
    )


def _skill_for(tool: ToolIR) -> GeneratedSkill:
    return GeneratedSkill(
        baseline_name="generated_skill_base",
        skill_summary=tool.tool_purpose or "",
        when_to_use=[tool.tool_purpose or ""],
        argument_template={"path": "docs"},
    )


class RoutingIntentBonusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = {
            "create_directory": _path_tool("create_directory", "Create a directory or ensure a directory exists."),
            "list_directory": _path_tool("list_directory", "List directory contents."),
        }
        self.skill_bank = {name: _skill_for(tool) for name, tool in self.tools.items()}

    def test_list_directory_request_does_not_boost_create_from_directory_word_alone(self) -> None:
        candidates = retrieve_candidate_tools("List the docs directory.", self.tools, top_k=2)["candidates"]

        self.assertEqual(candidates[0]["tool_name"], "list_directory")
        self.assertGreater(candidates[0]["score"], candidates[1]["score"])

    def test_generated_skill_router_selects_list_directory_on_dev_listing_fixture(self) -> None:
        task = EvalTask(
            task_id="dev_fixture_list_dir",
            tool_name="list_directory",
            user_request="List the docs directory.",
            expected_arguments={"path": "docs"},
            split="dev",
            tags=["literal", "directory_listing"],
        )

        routing = select_tool_for_task(task, "generated_skill_base", self.tools, self.skill_bank, top_k=2)

        self.assertEqual(routing["selected_tool_name"], "list_directory")

    def test_creation_request_still_routes_to_create_directory(self) -> None:
        candidates = retrieve_candidate_tools("Create the docs directory.", self.tools, top_k=2)["candidates"]

        self.assertEqual(candidates[0]["tool_name"], "create_directory")


if __name__ == "__main__":
    unittest.main()
