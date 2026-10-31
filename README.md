# portability-lint

![Tests](https://github.com/rahmankhanjohn/portability-lint/actions/workflows/test.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/rahmankhanjohn/badge.svg)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen.svg)
![Tests: 5](https://img.shields.io/badge/tests-5%20passing-brightgreen.svg)
![GitHub stars](https://img.shields.io/github/stars/rahmankhanjohn/portability-lint?style=social)
![Last commit](https://img.shields.io/github/last-commit/rahmankhanjohn/portability-lint)

Find what would break if this moved to another cloud, before you promise anyone portability.

Most teams believe they are portable because their code is in containers. Containers carry the runtime. They do not carry the storage backend, the IAM model, the managed database API, or the ingress controller that the platform happens to provide.

This tool reads a tree and separates the two kinds of dependency.

- **Blockers** — storage classes, cloud IAM resources, managed database APIs, cloud-specific kubelet settings. These move with the provider. A blocker means the second cloud is a rebuild, not a copy.
- **Soft dependencies** — image registries, provider CLIs, SDK imports, zonal node selectors, object store URLs. Usually replaceable, but they cost engineer time.

## Recognition

Indexed on the [XERJ Corpus Hub](https://hub.xerj.org/contributors/rahmankhanjohn) - the open reference memory AI coding agents search before they write code.

## Requirements

Python 3.9+, no dependencies.

## Usage

```
python3 portability_lint.py .
python3 portability_lint.py ./infra --json
```

```
Portability lint
==================================================================
  Path         /home/you/infra
  Files read   42

  Blockers (these move with the provider)
    storage_class            terraform/main.tf:31  ebs-csi
    terraform_aws            terraform/main.tf:12  resource "aws_instance"
    iam_role                 terraform/iam.tf:4   aws_iam_role

  Soft dependencies (usually replaceable)
    cloud_image              Dockerfile:3          public.ecr.aws
    zone_node_selector       k8s/deploy.yaml:18   topology.kubernetes.io/zone

  Files with a dependency  7 of 42
  Portability score         83%

  A blocker means the second cloud is a rebuild, not a copy.
  Budget for that before the first traffic cutover.
```

Exit code 0 when there are no blockers, 1 when there are.

## What it looks for

Terraform provider resources, cloud block provider stanzas, storage classes, cloud ingress annotations, cloud kubelet providers, zonal node selectors, managed database names, IAM resources, object store URLs, provider CLI calls, cloud image registries, cloud SDK imports and KMS or vault secret references.

## Windows

Download `portability-lint.exe` from the releases page, or run it with the Python launcher:

```
py portability_lint.py C:\path\to\repo
```

## Tests

```
python3 -m unittest test_portability_lint -v
```

## Where this comes from

Written while preparing *Multi-cloud: What Survives a Second Cloud*. The article argues that portability is a layering decision, and this tool is the part that tells you which layer you are actually standing on.

## License

MIT

## Who is this for?

No telemetry in this tool. If you use it, plan to, or rejected it, tell us your environment in [the discussion thread](https://github.com/rahmankhanjohn/portability-lint/discussions/1). Operator replies steer the roadmap.
