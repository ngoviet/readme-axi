# readme-axi

<!-- readme-axi type=tool -->

**English** · [Tiếng Việt](README.vi.md)

Checks that a repository's `README.md` (English) and `README.vi.md` (Vietnamese) follow the shared
ngoviet layout and stay in step with each other. One file, Python standard library only, output in
[TOON](https://toonformat.dev/) for agents; exit code 0 = pass, 1 = issues, 2 = bad usage.

## Installation

Nothing to install: `readme_axi.py` is a single file that runs on Python 3.9 or later with the standard
library only. Copy it anywhere, or download it from `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/ngoviet/readme-axi/main/readme_axi.py -o readme_axi.py
```

`drift` and the repository name read git history, so `git` must be on `PATH`.

## Usage

```bash
python3 readme_axi.py check [dir]            # layout, switcher line, required sections, EN/VI parity, support block
python3 readme_axi.py drift [dir] [--strict] # README.md commits not yet ported to README.vi.md
python3 readme_axi.py meta [dir]             # GitHub About box (needs gh): description, topics, license, preview
python3 readme_axi.py social [dir]           # render a 1280x640 social preview (SVG, PNG with Edge/Chrome)
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

`main` is what every repository's CI downloads, so a new support template never turns existing READMEs
red: a block written by readme-axi 0.2.x still passes with a `support-outdated` warning, and
`support --write` moves it to the current template. A block edited by hand is still an error.

### Links, images and size

`check` also reads the links and images outside code (fenced blocks, inline code and `<!-- -->`
comments): Markdown inline and reference-style links, images nested in links (badges), and the
`<a>`, `<img>` and `<source>` tags, also when a tag spans several lines.

- `link`: a relative link or image must point to a file in the repository, letter case included, as
  on GitHub and on Linux CI. Web links, anchors and paths that climb out of the repository
  (`../../issues`, `../other-repo`) are not checked.
- `alt`: every image needs alt text.
- `size`: a README over 500 KiB, because GitHub cuts the rest off.

These three rules warn without failing; `check --strict` fails on warnings too. Indented code blocks
(four spaces, no fence) are not recognised as code.

### The GitHub About box

GitHub search looks only at the repository name, description and topics unless the reader adds
`in:readme`, and Google uses the description as the page summary. `meta` reads them with `gh` and
reports a missing description or one over 120 characters, fewer than 5 topics or a badly formed one, no
license GitHub can detect, no social preview image, a README intro that tells a different story from the
description, and a `private` marker that disagrees with GitHub. Forks and the profile repository skip the
topic, license and preview rules. Without `gh` the command says so and exits 0.

GitHub has no API for the social preview image: `social` renders one (name, description, topics) for
you to upload in Settings > General > Social preview. GitHub lists topics almost alphabetically, so the
image shows up to five chosen by the description: topics it mentions come first, in reading order, and
look-alikes (`homeassistant` next to `home-assistant`) are dropped.

### Private repositories

Add `private` to the marker: `<!-- readme-axi type=ops private -->`, in both files. A private repository
keeps the bilingual layout (title and marker, switcher, intro, type sections, canonical names, EN/VI
parity, no emoji, `drift`) but needs no support block and no `## License`: nobody else reads it and the
code is not MIT licensed. `support --write` leaves a private repository alone.

When the repository goes public, drop `private` from the marker; `check` then lists what is missing
(support block, License).

## Configuration

Each public repository calls the reusable workflow in this repository (GitHub Actions):

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
    uses: ngoviet/readme-axi/.github/workflows/readme.yml@main
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
      - curl -fsSL https://raw.githubusercontent.com/ngoviet/readme-axi/main/readme_axi.py -o /tmp/readme_axi.py
      - python3 /tmp/readme_axi.py check
      - python3 /tmp/readme_axi.py drift
```

`main` of this public repository is the published copy, so the download needs no token. CI everywhere
runs that file: a change reaches every repository as soon as it lands on `main`.

## Development

```bash
python3 -m unittest discover -s . -v
```

The tests run the CLI on temporary READMEs (and temporary git repositories for `drift` and the
repository name). This README is itself checked: `python3 readme_axi.py check` must pass before a commit.

<!-- support:start -->
## Support the project

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner-v2.svg" width="560" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">Free and open source. Your support pays for new device support, faster fixes and every release.</p>

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
  &nbsp;
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">
</p>

<p align="center"><b>Crypto wallet, BNB Smart Chain (BEP20) only:</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>

<p align="center">🇻🇳 VietQR: scan with any Vietnamese banking app, transfer note <code>Ung ho readme-axi</code>. Thank you for keeping this project alive!</p>
<!-- support:end -->

## License

[MIT](LICENSE) © Ngô Đức Việt
