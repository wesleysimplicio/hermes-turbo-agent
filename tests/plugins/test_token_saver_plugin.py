from __future__ import annotations

from pathlib import Path

import yaml

import hermes_cli.plugins as plugins_mod
from plugins.token_saver.token_saver import (
    compress_command_output,
    compress_tool_result,
    estimate_tokens,
)


def test_compress_command_output_preserves_pytest_failure_and_saves_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    output = "\n".join(
        [
            "============================= test session starts =============================",
            "tests/test_example.py::test_ok PASSED",
            "tests/test_example.py::test_contract FAILED",
            "________________________________ test_contract ________________________________",
            "E       AssertionError: expected token savings",
            "E       assert False",
            "tests/test_example.py:42: AssertionError",
            *[f"noise line {i}" for i in range(120)],
            "=========================== short test summary info ===========================",
            "FAILED tests/test_example.py::test_contract - AssertionError: expected token savings",
            "1 failed, 1 passed in 0.31s",
        ]
    )

    compressed = compress_command_output(
        command="pytest -q",
        output=output,
        returncode=1,
        mode="safe",
        min_chars=200,
    )

    assert "token-saver-output" in compressed
    assert "pytest -q" in compressed
    assert "AssertionError: expected token savings" in compressed
    assert "tests/test_example.py:42" in compressed
    assert "1 failed, 1 passed" in compressed
    assert "noise line 119" not in compressed

    saved_line = next(line for line in compressed.splitlines() if line.startswith("saved_to:"))
    saved_path = Path(saved_line.split(":", 1)[1].strip())
    assert saved_path.exists()
    assert "noise line 119" in saved_path.read_text(encoding="utf-8")


def test_compress_command_output_leaves_exact_file_reads_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    output = "line 1\n" + ("A" * 3000)

    compressed = compress_command_output(
        command="cat README.md",
        output=output,
        returncode=0,
        mode="safe",
        min_chars=200,
    )

    assert compressed == output


def test_compress_command_output_reports_token_gain(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    output = "\n".join(f"modified: file_{i}.py" for i in range(200))

    compressed = compress_command_output(
        command="git status --short",
        output=output,
        returncode=0,
        mode="balanced",
        min_chars=100,
    )

    assert "estimated_raw_tokens:" in compressed
    assert "estimated_saved_tokens:" in compressed
    assert estimate_tokens(compressed) < estimate_tokens(output)


def test_compress_tool_result_keeps_read_file_results_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    result = "important source text\n" + ("x" * 2500)

    compressed = compress_tool_result(
        tool_name="read_file",
        result=result,
        mode="aggressive",
        min_chars=100,
    )

    assert compressed == result


def test_token_saver_plugin_registers_transform_hooks(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    plugin_dir = tmp_path / "home" / "plugins" / "token-saver"
    plugin_dir.mkdir(parents=True)
    source_dir = Path(__file__).resolve().parents[2] / "plugins" / "token_saver"
    (plugin_dir / "plugin.yaml").write_text(
        (source_dir / "plugin.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(
        (source_dir / "__init__.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (plugin_dir / "token_saver.py").write_text(
        (source_dir / "token_saver.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "home" / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["token-saver"]}}),
        encoding="utf-8",
    )

    original_manager = plugins_mod._plugin_manager
    try:
        plugins_mod._plugin_manager = plugins_mod.PluginManager()
        plugins_mod.discover_plugins(force=True)

        hooks = plugins_mod.get_plugin_manager()._hooks
        assert "transform_terminal_output" in hooks
        assert "transform_tool_result" in hooks
    finally:
        plugins_mod._plugin_manager = original_manager
