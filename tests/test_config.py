"""Tests for config.py — focused on JQL building and env parsing."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as cfg


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


class LoadEnvTest(unittest.TestCase):
    def setUp(self):
        self._saved = {}
        for k in ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "EXCLUDED_PROJECTS"]:
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


if __name__ == "__main__":
    unittest.main()
