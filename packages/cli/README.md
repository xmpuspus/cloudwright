# cloudwright-cli

Command-line interface for [Cloudwright](https://github.com/xmpuspus/cloudwright) architecture intelligence.

## Install

```bash
pip install 'cloudwright-ai[cli]'
```

## Usage

```bash
cloudwright design "3-tier web app on AWS"
cloudwright cost spec.yaml
cloudwright validate spec.yaml --compliance hipaa
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright diff v1.yaml v2.yaml
cloudwright catalog search "4 vcpu 16gb"
cloudwright migrate demo
cloudwright chat
```

## Migration commands

Migration planning and evidence checks run offline. They never copy data, apply infrastructure,
switch traffic, or run a cutover.

```bash
cloudwright migrate packs
cloudwright migrate plan project.yaml -o assessment.yaml
cloudwright migrate verify assessment.yaml evidence.yaml -o evidence-pack.yaml
cloudwright --json migrate demo
```

`migrate verify` exits with code 2 when blocking evidence fails or is missing. See the
[migration guide](https://github.com/xmpuspus/cloudwright/blob/main/docs/migrations.md) for the
project schema, pack format, Python API, and checked examples.

See the [main project README](https://github.com/xmpuspus/cloudwright) for full documentation.
