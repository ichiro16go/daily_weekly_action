"""Tests for config.py — JQL building, env parsing, subtask & excluded-project handling."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402


_BASE_ENV = {
    "JIRA_BASE_URL": "https://example.atlassian.net",
    "JIRA_EMAIL": "test@example.com",
    "JIRA_API_TOKEN": "dummy",
}


def _make_config(**overrides) -> cfg.Config:
    defaults = dict(
        base_url="https://example.atlassian.net",
        email="test@example.com",
        api_token="token",
        slack_webhook_url=None,
    )
    defaults.update(overrides)
    return cfg.Config(**defaults)


class ExcludedProjectsClauseTest(unittest.TestCase):
    def test_default_excludes_SYOUGYO(self):
        c = _make_config()
        self.assertEqual(c.excluded_projects, ["SYOUGYO"])

    def test_board_jql_appends_excluded_clause(self):
        c = _make_config(excluded_projects=["SYOUGYO"])
        jql = c.board_jql()
        self.assertIn("project NOT IN (SYOUGYO)", jql)

    def test_board_member_jql_appends_excluded_clause(self):
        c = _make_config(excluded_projects=["SYOUGYO", "FOO"])
        jql = c.board_member_jql()
        self.assertIn("project NOT IN (SYOUGYO, FOO)", jql)

    def test_empty_excluded_projects_omits_clause(self):
        c = _make_config(excluded_projects=[])
        jql = c.board_jql()
        self.assertNotIn("project NOT IN", jql)

    def test_board_jql_with_extra_keeps_exclusion(self):
        c = _make_config(excluded_projects=["SYOUGYO"])
        jql = c.board_jql('status = "In Progress"')
        self.assertIn("project NOT IN (SYOUGYO)", jql)
        self.assertIn('status = "In Progress"', jql)


class LoadEnvExcludedProjectsTest(unittest.TestCase):
    def setUp(self):
        self._saved = {}
        for k in ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "EXCLUDED_PROJECTS", "INCLUDE_SUBTASKS"]:
            self._saved[k] = os.environ.pop(k, None)
        os.environ["JIRA_BASE_URL"] = "https://example.atlassian.net"
        os.environ["JIRA_EMAIL"] = "test@example.com"
        os.environ["JIRA_API_TOKEN"] = "token"

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_excluded_when_env_missing(self):
        c = cfg.load()
        self.assertEqual(c.excluded_projects, ["SYOUGYO"])

    def test_env_override(self):
        os.environ["EXCLUDED_PROJECTS"] = "SYOUGYO,LEGACY,WIP"
        c = cfg.load()
        self.assertEqual(c.excluded_projects, ["SYOUGYO", "LEGACY", "WIP"])

    def test_empty_env_means_no_exclusion(self):
        os.environ["EXCLUDED_PROJECTS"] = ""
        c = cfg.load()
        self.assertEqual(c.excluded_projects, [])


class IncludeSubtasksDefaultTests(unittest.TestCase):
    def test_default_is_true(self) -> None:
        with patch.dict(os.environ, _BASE_ENV, clear=True):
            c = cfg.load()
        self.assertTrue(c.include_subtasks)

    def test_env_false_disables(self) -> None:
        env = {**_BASE_ENV, "INCLUDE_SUBTASKS": "false"}
        with patch.dict(os.environ, env, clear=True):
            c = cfg.load()
        self.assertFalse(c.include_subtasks)

    def test_env_zero_disables(self) -> None:
        env = {**_BASE_ENV, "INCLUDE_SUBTASKS": "0"}
        with patch.dict(os.environ, env, clear=True):
            c = cfg.load()
        self.assertFalse(c.include_subtasks)

    def test_env_true_enables(self) -> None:
        env = {**_BASE_ENV, "INCLUDE_SUBTASKS": "true"}
        with patch.dict(os.environ, env, clear=True):
            c = cfg.load()
        self.assertTrue(c.include_subtasks)


class StartDateFieldTests(unittest.TestCase):
    def test_default_is_customfield_10015(self) -> None:
        with patch.dict(os.environ, _BASE_ENV, clear=True):
            c = cfg.load()
        self.assertEqual(c.start_date_field, "customfield_10015")

    def test_env_override(self) -> None:
        env = {**_BASE_ENV, "JIRA_START_DATE_FIELD": "customfield_12345"}
        with patch.dict(os.environ, env, clear=True):
            c = cfg.load()
        self.assertEqual(c.start_date_field, "customfield_12345")

    def test_env_empty_disables(self) -> None:
        env = {**_BASE_ENV, "JIRA_START_DATE_FIELD": ""}
        with patch.dict(os.environ, env, clear=True):
            c = cfg.load()
        self.assertEqual(c.start_date_field, "")


class BoardJqlSubtaskClauseTests(unittest.TestCase):
    def _make(self, include: bool) -> cfg.Config:
        return _make_config(include_subtasks=include)

    def test_include_true_omits_subtask_exclusion(self) -> None:
        c = self._make(True)
        jql = c.board_jql()
        self.assertNotIn("Sub-task", jql)
        self.assertNotIn("サブタスク", jql)

    def test_include_false_adds_subtask_exclusion(self) -> None:
        c = self._make(False)
        jql = c.board_jql()
        self.assertIn("Sub-task", jql)
        self.assertIn("サブタスク", jql)

    def test_member_jql_include_true_omits_subtask_exclusion(self) -> None:
        c = self._make(True)
        jql = c.board_member_jql()
        self.assertNotIn("Sub-task", jql)

    def test_member_jql_include_false_adds_subtask_exclusion(self) -> None:
        c = self._make(False)
        jql = c.board_member_jql()
        self.assertIn("Sub-task", jql)

    def test_extra_clause_appended_with_subtask_exclusion(self) -> None:
        c = self._make(False)
        jql = c.board_jql(extra='status = "In Progress"')
        self.assertIn("Sub-task", jql)
        self.assertIn('AND status = "In Progress"', jql)


if __name__ == "__main__":
    unittest.main()
