"""The `.env` loader: it must fill gaps, never open the LLM gate, never show a value."""

from __future__ import annotations

from app.envfile import load_poc_env, parse_env_file


def test_key_value_lines_are_parsed():
    assert parse_env_file("POC_A=1\nPOC_B=two words\n") == {"POC_A": "1", "POC_B": "two words"}


def test_comments_and_blank_lines_are_skipped():
    text = "# a comment\n\nPOC_A=1\n   # indented comment\n# POC_B=commented_out\n"
    assert parse_env_file(text) == {"POC_A": "1"}


def test_one_pair_of_matching_quotes_is_dropped():
    assert parse_env_file('POC_A="x y"\nPOC_B=\'z\'\nPOC_C="mismatched\'\n') == {
        "POC_A": "x y",
        "POC_B": "z",
        "POC_C": "\"mismatched'",
    }


def test_a_value_may_itself_contain_an_equals_sign():
    """Database URLs do: `?sslmode=require` style suffixes."""
    assert parse_env_file("POC_URL=postgresql://u:p@h/db?a=b\n") == {
        "POC_URL": "postgresql://u:p@h/db?a=b"
    }


def test_an_export_prefix_is_tolerated():
    assert parse_env_file("export POC_A=1\n") == {"POC_A": "1"}


def test_only_poc_keys_are_loaded(tmp_path):
    (tmp_path / ".env").write_text("POC_DATABASE_URL=x\nSOMETHING_ELSE=y\n", encoding="utf-8")
    env: dict[str, str] = {}
    assert load_poc_env(tmp_path / ".env", env) == ["POC_DATABASE_URL"]
    assert env == {"POC_DATABASE_URL": "x"}


def test_the_live_call_gate_can_never_be_opened_from_a_file(tmp_path):
    """RULEBOOK §2 rule 7. An uncommented line in .env must not spend money."""
    (tmp_path / ".env").write_text("CALIBER_ALLOW_LLM=1\nPOC_A=1\n", encoding="utf-8")
    env: dict[str, str] = {}
    load_poc_env(tmp_path / ".env", env)
    assert "CALIBER_ALLOW_LLM" not in env


def test_a_variable_that_is_already_set_wins_over_the_file(tmp_path):
    (tmp_path / ".env").write_text("POC_DATABASE_URL=from_file\n", encoding="utf-8")
    env = {"POC_DATABASE_URL": "from_shell"}
    assert load_poc_env(tmp_path / ".env", env) == []
    assert env["POC_DATABASE_URL"] == "from_shell"


def test_a_missing_file_is_not_an_error(tmp_path):
    """The offline suite runs with no .env at all, on purpose."""
    assert load_poc_env(tmp_path / "absent.env", {}) == []


def test_only_key_names_are_reported_never_values(tmp_path):
    (tmp_path / ".env").write_text("POC_DATABASE_URL=postgresql://u:hunter2@h/d\n", encoding="utf-8")
    reported = load_poc_env(tmp_path / ".env", {})
    assert reported == ["POC_DATABASE_URL"]
    assert "hunter2" not in repr(reported)
