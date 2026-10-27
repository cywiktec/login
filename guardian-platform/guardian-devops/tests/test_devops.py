import os
import tempfile
import unittest

from guardian_devops import artifacts, docker_compose as dc, github_actions as ga
from guardian_devops import releases, secrets


class GithubActionsTests(unittest.TestCase):
    def test_generated_workflow_lints_clean(self):
        self.assertEqual(ga.lint(ga.test_workflow(["guardian-core"])), [])
        self.assertEqual(ga.lint(ga.release_workflow()), [])

    def test_bad_component_rejected(self):
        with self.assertRaises(ValueError):
            ga.test_workflow(["a; rm -rf /"])
        with self.assertRaises(ValueError):
            ga.test_workflow([])

    def test_lint_finds_problems(self):
        wf = {"on": {"pull_request_target": {}}, "jobs": {"j": {"steps": [
            {"uses": "foo/bar"}, {"uses": "foo/bar@main"},
            {"run": "echo ${{ github.event.issue.title }}"}]}}}
        text = " | ".join(ga.lint(wf))
        for word in ("permissions", "pull_request_target", "timeout", "unpinned", "moving", "injection"):
            self.assertIn(word, text)

    def test_render_quotes_expressions(self):
        out = ga.render(ga.test_workflow(["guardian-core"]))
        self.assertIn('"on":', out)
        self.assertIn('"${{ matrix.python }}"', out)


class ComposeTests(unittest.TestCase):
    def test_default_stack_valid(self):
        self.assertEqual(dc.validate(dc.default_stack()), [])
        self.assertIn("127.0.0.1:9090:9090", dc.render(dc.default_stack()))

    def test_unpinned_image_refused(self):
        with self.assertRaises(ValueError):
            dc.service("nginx")

    def test_validate_flags(self):
        bad = {"services": {"x": {"image": "x:latest", "privileged": True, "network_mode": "host",
                                  "volumes": ["/var/run/docker.sock:/s"], "ports": ["80:80"],
                                  "environment": {"DB_PASSWORD": "hunter2"}}}}
        text = " | ".join(dc.validate(bad))
        for word in ("not pinned", "privileged", "host network", "docker socket",
                     "all interfaces", "literal secret"):
            self.assertIn(word, text)
        self.assertEqual(dc.validate({}), ["no services"])

    def test_env_reference_allowed(self):
        c = {"services": {"x": {"image": "x:1", "environment": {"TOKEN": "${TOKEN}"}}}}
        self.assertEqual(dc.validate(c), [])


class ReleaseTests(unittest.TestCase):
    def test_bump(self):
        self.assertEqual(releases.bump("0.1.9", "patch"), "0.1.10")
        self.assertEqual(releases.bump("0.1.9", "minor"), "0.2.0")
        self.assertEqual(releases.bump("1.2.3", "major"), "2.0.0")

    def test_invalid_versions(self):
        for v in ("1.2", "01.2.3", "1.2.3-rc1", "v1.2.3", ""):
            with self.assertRaises(ValueError):
                releases.parse(v)
        with self.assertRaises(ValueError):
            releases.bump("1.0.0", "huge")

    def test_changelog(self):
        out = releases.changelog_entry("# Changelog\n\nold\n", "0.2.0", "2026-01-02", ["x"])
        self.assertIn("## [0.2.0] - 2026-01-02\n- x", out)
        self.assertTrue(out.startswith("# Changelog"))
        with self.assertRaises(ValueError):
            releases.changelog_entry(out, "0.2.0", "2026-01-03", ["y"])
        with self.assertRaises(ValueError):
            releases.changelog_entry(out, "0.3.0", "bad", ["y"])
        with self.assertRaises(ValueError):
            releases.changelog_entry(out, "0.3.0", "2026-01-03", [])

    def test_check_release(self):
        self.assertTrue(releases.check_release("0.1.0", "v0.1.0", "0.1.0\n"))
        self.assertFalse(releases.check_release("0.1.0", "v0.1.1", "0.1.0"))
        self.assertFalse(releases.check_release("0.1.0", "v0.1.0", "0.2.0"))


class SecretsTests(unittest.TestCase):
    def test_detects(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nghp_" + "a1B2c3D4" * 5 + "\npassword = Xk39sLq02mZp\n"
        kinds = {k for _, _, k in secrets.scan_text(text)}
        self.assertEqual(kinds, {"private_key", "github_token", "assignment"})

    def test_ignores_placeholders(self):
        self.assertEqual(secrets.scan_text("password: ${DB_PASSWORD}\ntoken = changeme\npassword=aaaaaaaaaa"), [])

    def test_findings_never_contain_value(self):
        f = secrets.scan_text("api_key = Xk39sLq02mZp")
        self.assertNotIn("Xk39", repr(f))

    def test_redact(self):
        out = secrets.redact("password = Xk39sLq02mZp and AKIAABCDEFGHIJKLMNOP")
        self.assertNotIn("Xk39", out)
        self.assertNotIn("AKIA", out)

    def test_unreadable_file_is_finding(self):
        self.assertEqual(secrets.scan_files(["/nonexistent/x"])[0][2], "unreadable")

    def test_require_env(self):
        self.assertEqual(secrets.require_env(["A", "B", "C"], {"A": "1", "B": ""}), ["B", "C"])


class ArtifactTests(unittest.TestCase):
    def test_manifest_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sub"))
            for n, c in (("a.txt", "1"), ("sub/b.txt", "2")):
                with open(os.path.join(d, n), "w") as f:
                    f.write(c)
            artifacts.write_manifest(d, "0.1.0")
            self.assertEqual(artifacts.verify(d), [])
            with open(os.path.join(d, "a.txt"), "w") as f:
                f.write("changed")
            os.remove(os.path.join(d, "sub/b.txt"))
            with open(os.path.join(d, "extra"), "w") as f:
                f.write("x")
            self.assertEqual(sorted(artifacts.verify(d)),
                             ["missing: sub/b.txt", "modified: a.txt", "unexpected: extra"])

    def test_missing_or_corrupt_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(artifacts.verify(d), ["manifest missing or invalid"])
            with open(os.path.join(d, "MANIFEST.json"), "w") as f:
                f.write("{")
            self.assertEqual(artifacts.verify(d), ["manifest missing or invalid"])


if __name__ == "__main__":
    unittest.main()
