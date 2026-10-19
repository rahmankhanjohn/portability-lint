import json
import os
import tempfile
import unittest
from pathlib import Path

import portability_lint as pl

FIXTURE = '''
resource "aws_instance" "web" {
  ami = "ami-0abc123"
  tags = {
    Name = "web-01"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "example-logs"
}

resource "kubernetes_pod" "api" {
  spec = {
    nodeSelector {
      "topology.kubernetes.io/zone" = "us-east-1a"
    }
    storageClassName: "ebs-csi"
  }
}
'''


class TestExtraction(unittest.TestCase):
    def test_finds_aws_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'main.tf').write_text(FIXTURE)
            findings, scanned = pl.scan(root)
            self.assertTrue(findings)
            self.assertEqual(scanned, 1)

    def test_blockers_and_soft_are_separated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'main.tf').write_text(FIXTURE)
            findings, scanned = pl.scan(root)
            rules = {f['rule'] for f in findings}
            self.assertIn('terraform_aws', rules)
            self.assertIn('storage_class', rules)
            self.assertIn('zone_node_selector', rules)
            blockers = [f for f in findings if f['severity'] == 'blocker']
            soft = [f for f in findings if f['severity'] == 'soft']
            self.assertTrue(blockers)
            self.assertTrue(soft)

    def test_reports_line_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'main.tf').write_text(FIXTURE)
            findings, _ = pl.scan(root)
            for finding in findings:
                self.assertGreaterEqual(finding['line'], 1)
                self.assertTrue(finding['file'].endswith('main.tf'))

    def test_clean_tree_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'app.py').write_text('def main():\n    return 0\n')
            findings, scanned = pl.scan(root)
            self.assertEqual(findings, [])
            self.assertEqual(scanned, 1)

    def test_skip_directories(self):
        self.assertIn('.git', pl.SKIP_DIRS)
        self.assertIn('node_modules', pl.SKIP_DIRS)


if __name__ == '__main__':
    unittest.main()
