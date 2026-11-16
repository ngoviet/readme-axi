# readme-axi

<!-- readme-axi type=tool private -->

**English** · [Tiếng Việt](README.vi.md)

Checks that a repository's `README.md` (English) and `README.vi.md` (Vietnamese) follow the shared
ngoviet layout and stay in step with each other. One file, Python standard library only, output in
[TOON](https://toonformat.dev/) for agents; exit code 0 = pass, 1 = issues, 2 = bad usage.

## Installation

Nothing to install: `readme_axi.py` is a single file that runs on Python 3.9 or later with the standard
library only. Copy it anywhere, or download the published copy:

```bash
curl -fsSL https://raw.githubusercontent.com/ngoviet/.github/main/readme-axi/readme_axi.py -o readme_axi.py
```

`drift` and the repository name read git history, so `git` must be on `PATH`.

## Usage

```bash
python3 readme_axi.py check [dir]            # layout, switcher line, required sections, EN/VI parity, support block
python3 readme_axi.py drift [dir] [--strict] # README.md commits not yet ported to README.vi.md
python3 readme_axi.py support [dir] --write  # insert/refresh the shared "Support the project" block
python3 readme_axi.py scaffold --type ha --title "Name for Home Assistant"
python3 readme_axi.py scaffold --type ops --title "nas" --private   # private repo skeleton
python3 readme_axi.py names                  # canonical section names EN -> VI and required order
```

## How it works

### The layout

Every README starts the same way:

1. `# Title` on the first line, then the marker `<!-- readme-axi type=<type> -->`
   (`<!-- readme-axi type=<type> private -->` in a private repository).
2. Badges, then the language switcher — `**English** · [Tiếng Việt](README.vi.md)` in README.md,
   `[English](README.md) · **Tiếng Việt**` in README.vi.md.
3. One paragraph: what it does, for which device. Optional install button, one-line support callout,
   screenshot.

and, in a public repository, ends the same way: the shared support block, then `## License` / `## Giấy phép`
(`[MIT](LICENSE) © Ngô Đức Việt`, plus "Not affiliated with …" when the project targets a vendor's device).

Required `##` sections, in this order (others may sit in between):

| Type | Required |
|---|---|
| `ha` integration | Features · Installation · Configuration · Entities · Troubleshooting · Development |
| `card` Lovelace card / theme | Features · Installation · Usage |
| `esp32` ESPHome device | Features · Hardware · Quick start · Home Assistant |
| `tool` CLI / library | Installation · Usage |
| `app` web app / service | Features · Development · Deployment |
| `ops` operations repo (scripts, servers) | Usage · Project layout |
| `config` configuration repo | Project layout · Deployment |
| `docs` documents, notes | Project layout |

Both files have the same number of `##` sections, in the same order, with the canonical names
(`readme_axi.py names`). Headings carry no emoji, so anchors stay clean.

The support block carries the repository name. It comes from `--repo`, then from the `origin` remote,
then from the folder name, so a worktree or a temporary clone checks against the right name.

### Private repositories

Add `private` to the marker: `<!-- readme-axi type=ops private -->`, in both files. A private repository
keeps the bilingual layout (title and marker, switcher, intro, type sections, canonical names, EN/VI
parity, no emoji, `drift`) but needs no support block and no `## License`: nobody else reads it and the
code is not MIT licensed. `support --write` leaves a private repository alone.

When the repository goes public, drop `private` from the marker; `check` then lists what is missing
(support block, License).

## Configuration

Each public repository calls the reusable workflow in `ngoviet/.github` (GitHub Actions):

```yaml
# .github/workflows/readme.yml
name: README
on:
  push:
    paths: [README.md, README.vi.md]
  pull_request:
    paths: [README.md, README.vi.md]
jobs:
  readme:
    uses: ngoviet/.github/.github/workflows/readme.yml@main
```

Private repositories run on the self-hosted Woodpecker at https://ci.vokupt.top (GitHub Actions
has no minutes left for private repositories). The repository must be enabled there and carry this file:

```yaml
# .woodpecker/readme.yaml
when:
  - event: pull_request
    path: [README.md, README.vi.md, .woodpecker/readme.yaml]
  - event: push
    branch: main
    path: [README.md, README.vi.md, .woodpecker/readme.yaml]
  - event: manual

clone:
  - name: clone
    image: woodpeckerci/plugin-git
    settings:
      partial: false # drift reads git history: full clone, not shallow
      depth: 0

steps:
  - name: readme
    image: python:3.13-bookworm # python3, git and curl included
    commands:
      - git config --global --add safe.directory "$CI_WORKSPACE"
      - curl -fsSL https://raw.githubusercontent.com/ngoviet/.github/main/readme-axi/readme_axi.py -o /tmp/readme_axi.py
      - python3 /tmp/readme_axi.py check
      - python3 /tmp/readme_axi.py drift
```

The published copy lives in the public `ngoviet/.github` repository (`readme-axi/readme_axi.py`), so the
download needs no token. After changing this repository, copy `readme_axi.py` there: CI everywhere runs
that copy.

## Development

```bash
python3 -m unittest discover -s . -v
```

The tests run the CLI on temporary READMEs (and temporary git repositories for `drift` and the
repository name). This README is itself checked: `python3 readme_axi.py check` must pass before a commit.
