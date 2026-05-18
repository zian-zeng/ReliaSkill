import unittest

from autoskill.experiment import _safe_task_name as benchmark_task_name
from autoskill.routing_eval import _safe_task_name as routing_task_name


class TaskArtifactPathTest(unittest.TestCase):
    def test_long_task_names_keep_distinct_cache_paths(self) -> None:
        prefix = "ctrl_" + "very_long_tool_name_" * 8
        first = prefix + "negative_hard_0_similar_tool_should_be_used"
        second = prefix + "negative_hard_1_similar_tool_should_be_used"

        self.assertNotEqual(benchmark_task_name(first), benchmark_task_name(second))
        self.assertNotEqual(routing_task_name(first), routing_task_name(second))
        self.assertLessEqual(len(benchmark_task_name(first)), 96)
        self.assertLessEqual(len(routing_task_name(first)), 96)


if __name__ == "__main__":
    unittest.main()
