
"""
Unit tests for ``tools.code_extractor``.

Covers:
  • Extraction of single and multiple Python blocks
  • Handling of non-Python blocks (should be ignored)
  • Empty input
  • Mixed language blocks
"""

import pytest

from tools.code_extractor import extract_python_blocks


class TestExtractPythonBlocks:
    """Tests for ``extract_python_blocks``."""

    def test_single_python_block(self) -> None:
        md = (
            "# Example\n\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        result = extract_python_blocks(md)
        assert result == ["print('hello')"]

    def test_multiple_python_blocks(self) -> None:
        md = (
            "```python\n"
            "x = 1\n"
            "```\n"
            "\nSome text\n\n"
            "```python\n"
            "y = 2\n"
            "```\n"
        )
        result = extract_python_blocks(md)
        assert len(result) == 2
        assert result[0] == "x = 1"
        assert result[1] == "y = 2"

    def test_py_shorthand_fence(self) -> None:
        md = "```py\nprint(42)\n```\n"
        result = extract_python_blocks(md)
        assert result == ["print(42)"]

    def test_ignores_non_python_blocks(self) -> None:
        md = (
            "```javascript\n"
            "console.log('hi');\n"
            "```\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
        )
        result = extract_python_blocks(md)
        assert result == []

    def test_empty_input(self) -> None:
        assert extract_python_blocks("") == []

    def test_no_code_blocks(self) -> None:
        md = "# Title\n\nJust some markdown without code.\n"
        assert extract_python_blocks(md) == []

    def test_mixed_languages(self) -> None:
        md = (
            "```python\n"
            "a = 1\n"
            "```\n"
            "```javascript\n"
            "let b = 2;\n"
            "```\n"
            "```python\n"
            "c = 3\n"
            "```\n"
        )
        result = extract_python_blocks(md)
        assert len(result) == 2
        assert result[0] == "a = 1"
        assert result[1] == "c = 3"

    def test_multiline_block(self) -> None:
        md = (
            "```python\n"
            "def greet(name):\n"
            "    return f'Hello, {name}!'\n"
            "\n"
            "print(greet('World'))\n"
            "```\n"
        )
        result = extract_python_blocks(md)
        assert len(result) == 1
        assert "def greet(name):" in result[0]
        assert "print(greet('World'))" in result[0]
