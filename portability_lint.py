#!/usr/bin/env python3
"""portability-lint: find what would break if this moved to another cloud.

Scans a directory for cloud-specific dependencies and separates the blockers
(storage backends, IAM, managed databases) from the soft ones (image registries,
CLI calls, zone labels).

Usage:
  portability-lint.py [PATH] [--json] [--format table]
  portability-lint.py . --ext .tf,.yaml,.yml,.sh,.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# (rule, severity, provider hint, compiled regex)
RULES = [
    ('terraform_aws', 'blocker', 'AWS', re.compile(r'\bresource\s+"aws_[a-z0-9_]+"')),
    ('terraform_gcp', 'blocker', 'GCP', re.compile(r'\bresource\s+"(google_[a-z0-9_]+|google-beta_[a-z0-9_]+)"')),
    ('terraform_azure', 'blocker', 'Azure', re.compile(r'\bresource\s+"azurerm_[a-z0-9_]+"')),
    ('terraform_other', 'soft', 'other cloud', re.compile(r'\bresource\s+"(alicloud|openstack|oci|ibmcloud|huaweicloud|tencentcloud)_[a-z0-9_]+"')),
    ('provider_block', 'soft', 'any', re.compile(r'\bprovider\s+"(aws|google|azurerm|alicloud|openstack|oci|ibmcloud)"')),
    ('storage_class', 'blocker', 'any cloud CSI', re.compile(r'storageClassName:\s*["\']?(ebs-csi|pd-standard|disk|premium|file|standard[a-z]*)')),
    ('k8s_cloud_annotation', 'soft', 'cloud ingress', re.compile(r'(service\.beta\.kubernetes\.io/|kubernetes\.io/ingress-class|cloud\.google\.com/)')),
    ('k8s_cloud_provider', 'blocker', 'cloud provider', re.compile(r'--cloud-provider[= ][a-z]+|providerID:\s*["\']?[a-z]+\.cci\.')),
    ('zone_node_selector', 'soft', 'zonal topology', re.compile(r'topology\.kubernetes\.io/zone')),
    ('managed_db', 'blocker', 'managed service', re.compile(r'\b(rds|aurora|cloud_sql|azurerm_postgresql|cloudsql)\b', re.I)),
    ('iam_role', 'blocker', 'IAM', re.compile(r'\b(aws_iam_role|aws_iam_policy|google_service_account|azurerm_role_assignment)\b')),
    ('object_store_url', 'soft', 'object store', re.compile(r'\b(s3\.amazonaws\.com|storage\.googleapis\.com|blob\.core\.windows\.net|myqcloud\.com)')),
    ('cloud_cli', 'soft', 'provider CLI', re.compile(r'\b(aws|gcloud|az|aliyun|doctl|openstack)\s+(s3|ec2|compute|gcloud|vm|blob|nova|cloud|s3api)\b')),
    ('cloud_image', 'soft', 'registry', re.compile(r'\b(public\.ecr\.aws|gcr\.io|ghcr\.io|mcr\.microsoft\.com|docker\.io|quay\.io)\b')),
    ('cloud_sdk_import', 'soft', 'SDK', re.compile(r'\b(boto3|google\.cloud|azure\.storage\.blob|aliyunsdkcore)\b')),
    ('kms_secret_ref', 'soft', 'secret backend', re.compile(r'(arn:aws:secretsmanager|projects/[^/]+/secrets|keyvault|vault\.hashicorp)')),
]

SKIP_DIRS = {'.git', '.terraform', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.idea', '.vscode'}
DEFAULT_EXT = {'.tf', '.tfvars', '.yaml', '.yml', '.json', '.sh', '.py', '.go', '.java', '.js', '.ts', '.dockerfile', 'dockerfile'}


def should_scan(path):
    name = path.name.lower()
    if name in SKIP_DIRS:
        return False
    if path.suffix.lower() in DEFAULT_EXT or name.startswith('dockerfile'):
        return True
    return path.suffix == '' and name in ('dockerfile', 'makefile')


def scan(root):
    findings = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if not should_scan(path):
                continue
            try:
                text = path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            scanned += 1
            rel = str(path.relative_to(root)).replace('\\', '/')
            for rule, severity, hint, pattern in RULES:
                for match in pattern.finditer(text):
                    line = text.count('\n', 0, match.start()) + 1
                    snippet = match.group(0)[:60]
                    findings.append({'rule': rule, 'severity': severity, 'hint': hint,
                                     'file': rel, 'line': line, 'match': snippet})
    return findings, scanned


def portable_files(findings, scanned_files):
    blocked = {f['file'] for f in findings}
    return max(0, scanned_files - len(blocked))


def render(findings, scanned, root):
    lines = []
    lines.append('Portability lint')
    lines.append('=' * 66)
    lines.append('  Path         %s' % root)
    lines.append('  Files read   %d' % scanned)
    lines.append('')
    if not findings:
        lines.append('  No cloud-specific dependencies found.')
        lines.append('  This tree looks portable as it stands.')
        return '\n'.join(lines)

    blockers = [f for f in findings if f['severity'] == 'blocker']
    soft = [f for f in findings if f['severity'] == 'soft']
    lines.append('  Blockers (these move with the provider)')
    for f in blockers:
        lines.append('    %-22s %s:%d  %s' % (f['rule'], f['file'], f['line'], f['match']))
    if not blockers:
        lines.append('    none')
    lines.append('')
    lines.append('  Soft dependencies (usually replaceable)')
    for f in soft:
        lines.append('    %-22s %s:%d  %s' % (f['rule'], f['file'], f['line'], f['match']))
    if not soft:
        lines.append('    none')
    lines.append('')
    affected = len({f['file'] for f in findings})
    score = 100.0 * (scanned - affected) / scanned if scanned else 0.0
    lines.append('  Files with a dependency  %d of %d' % (affected, scanned))
    lines.append('  Portability score         %.0f%%' % score)
    lines.append('')
    if blockers:
        lines.append('  A blocker means the second cloud is a rebuild, not a copy.')
        lines.append('  Budget for that before the first traffic cutover.')
    return '\n'.join(lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Find what would break if this moved to another cloud.')
    parser.add_argument('path', nargs='?', default='.', help='directory or file to scan')
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if root.is_file():
        findings, scanned = scan(root.parent)
        findings = [f for f in findings if f['file'] == root.name]
        scanned = 1 if findings or True else 0
    else:
        findings, scanned = scan(root)

    if args.json:
        print(json.dumps({'root': str(root), 'files_scanned': scanned,
                          'findings': findings}, indent=2))
    else:
        print(render(findings, scanned, str(root)))
    blockers = len([f for f in findings if f['severity'] == 'blocker'])
    return 1 if blockers else 0


if __name__ == '__main__':
    sys.exit(main())
