"""Tests for agent/contracts/concise_response.py (issue #101)."""

from __future__ import annotations

import unittest

from agent.contracts.concise_response import (
    ConciseContractError,
    Diagnostic,
    TerseAnswer,
    ToolCall,
    enforce_budget,
)


class EnforceBudgetTests(unittest.TestCase):
    def test_short_value_is_unchanged(self) -> None:
        self.assertEqual(enforce_budget("hi", 10), "hi")
        self.assertEqual(enforce_budget("abcde", 5), "abcde")

    def test_long_value_is_truncated_with_ellipsis(self) -> None:
        result = enforce_budget("x" * 50, 10)
        self.assertEqual(len(result), 10)
        self.assertEqual(result, "xxxxxxx...")

    def test_rejects_bad_input(self) -> None:
        with self.assertRaises(ConciseContractError):
            enforce_budget("any", 2)
        with self.assertRaises(ConciseContractError):
            enforce_budget(123, 10)  # type: ignore[arg-type]


class TerseAnswerTests(unittest.TestCase):
    def test_text_truncates_when_over_budget(self) -> None:
        answer = TerseAnswer(text="a" * (TerseAnswer.MAX_CHARS + 200))
        self.assertEqual(len(answer.text), TerseAnswer.MAX_CHARS)
        self.assertTrue(answer.text.endswith("..."))

    def test_short_text_is_unchanged(self) -> None:
        self.assertEqual(TerseAnswer(text="short").text, "short")

    def test_citations_capped_and_truncated(self) -> None:
        big = "c" * (TerseAnswer.MAX_CITATION_CHARS + 50)
        cits = [big] * (TerseAnswer.MAX_CITATIONS + 3)
        answer = TerseAnswer(text="t", citations=cits)
        self.assertEqual(len(answer.citations), TerseAnswer.MAX_CITATIONS)
        for c in answer.citations:
            self.assertEqual(len(c), TerseAnswer.MAX_CITATION_CHARS)
            self.assertTrue(c.endswith("..."))

    def test_to_dict(self) -> None:
        self.assertEqual(
            TerseAnswer(text="hello", citations=["a"]).to_dict(),
            {"text": "hello", "citations": ["a"]},
        )


class ToolCallTests(unittest.TestCase):
    def test_name_truncates(self) -> None:
        call = ToolCall(name="n" * (ToolCall.MAX_NAME_CHARS + 10))
        self.assertEqual(len(call.name), ToolCall.MAX_NAME_CHARS)
        self.assertTrue(call.name.endswith("..."))

    def test_empty_name_rejected(self) -> None:
        with self.assertRaises(ConciseContractError):
            ToolCall(name="")

    def test_args_capped_and_truncated(self) -> None:
        big = "v" * (ToolCall.MAX_ARG_VALUE_CHARS + 80)
        pairs = [(f"k{i}", big) for i in range(ToolCall.MAX_ARGS + 5)]
        call = ToolCall(name="t", args=pairs)
        self.assertEqual(len(call.args), ToolCall.MAX_ARGS)
        self.assertEqual(len(call.args[0][1]), ToolCall.MAX_ARG_VALUE_CHARS)
        self.assertTrue(call.args[0][1].endswith("..."))

    def test_arg_must_be_pair(self) -> None:
        with self.assertRaises(ConciseContractError):
            ToolCall(name="t", args=[("only",)])  # type: ignore[list-item]

    def test_to_dict(self) -> None:
        self.assertEqual(
            ToolCall(name="search", args=[("q", "isa")]).to_dict(),
            {"name": "search", "args": [["q", "isa"]]},
        )


class DiagnosticTests(unittest.TestCase):
    def test_level_normalised_and_validated(self) -> None:
        self.assertEqual(Diagnostic("ERROR", "E", "m").level, "error")
        with self.assertRaises(ConciseContractError):
            Diagnostic(level="fatal", code="E", message="m")

    def test_empty_code_rejected(self) -> None:
        with self.assertRaises(ConciseContractError):
            Diagnostic(level="info", code="", message="m")

    def test_message_truncates(self) -> None:
        big = "m" * (Diagnostic.MAX_MESSAGE_CHARS + 100)
        diag = Diagnostic(level="warning", code="W", message=big)
        self.assertEqual(len(diag.message), Diagnostic.MAX_MESSAGE_CHARS)
        self.assertTrue(diag.message.endswith("..."))

    def test_to_dict(self) -> None:
        self.assertEqual(
            Diagnostic(level="info", code="OK", message="all good").to_dict(),
            {"level": "info", "code": "OK", "message": "all good"},
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
