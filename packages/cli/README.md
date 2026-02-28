# cloudwright-ai-cli

Command-line interface for [Cloudwright](https://github.com/xmpuspus/cloudwright) architecture intelligence.

## Install

```bash
pip install cloudwright-ai[cli]
```

## Usage

```bash
cloudwright design "3-tier web app on AWS"
cloudwright cost spec.yaml
cloudwright validate spec.yaml --compliance hipaa
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright diff v1.yaml v2.yaml
cloudwright catalog search "4 vcpu 16gb"
cloudwright chat
```

See the [main project README](https://github.com/xmpuspus/cloudwright) for full documentation.
