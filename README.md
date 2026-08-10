# Repo Health Checker

Repo Health Checker is a read-only Python CLI that evaluates the documentation,
test structure, CI setup, Git state, and repository hygiene of a local Git
working tree. It produces a deterministic score and never runs the analyzed
project's code.

Version 1.0.0 provides the complete local, read-only analysis workflow.

## Features

- Accepts a repository root or any nested directory.
- Collects branch, HEAD, remotes, and staged/unstaged/untracked counts safely.
- Checks README, license, `.gitignore`, Python metadata, contributor docs, tests,
  GitHub Actions, suspicious paths, and large tracked files.
- Does not follow symlinked directories or read files to search for secrets.
- Produces terminal and stable JSON reports using only the standard library.

## Requirements and installation

- Python 3.11 or newer
- Git

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
python -m pip install --editable ".[dev]"
```

## Usage

```bash
repo-health-checker check C:/projects/example
python -m repo_health_checker check C:/projects/example
repo-health-checker check C:/projects/example --format json
repo-health-checker check C:/projects/example --large-file-limit-mib 25
```

The default large-file threshold is **10 MiB**. Run
`repo-health-checker check --help` for command help.

## Terminal report

```text
Repo Health Checker
Repository: C:\projects\example
Branch: main
Score: 90/100
Summary: 12 PASS, 2 WARN, 0 FAIL, 0 SKIP

Checks:
[PASS] README
  A top-level README is present.
[WARN] GitHub Actions (-10)
  No GitHub Actions workflow was found.
  Recommendation: Add a workflow under .github/workflows/.
```

## JSON report

JSON output has schema version `1.0` and contains the application version,
timestamp, requested and resolved paths, score, summary, Git facts, and ordered
check results. In JSON mode stdout contains only the JSON document; errors go to
stderr.

```json
{
  "schema_version": "1.0",
  "application_version": "1.0.0",
  "score": 90,
  "summary": {"pass": 12, "warn": 2, "fail": 0, "skip": 0, "total": 14}
}
```

## Scoring

Analysis begins at 100 and applies these transparent deductions, clamped at 0:

| Check | Missing/risky deduction | Result |
| --- | ---: | --- |
| HEAD / branch / remote / clean tree | 3–5 each | WARN |
| README / license / `.gitignore` | 10 each | FAIL |
| Python metadata / contributor docs | 5 / 2 | WARN |
| Test structure | 15 | FAIL |
| GitHub Actions | 10 | WARN |
| Tracked suspicious paths | 20 | FAIL |
| Untracked suspicious paths | 5 | WARN |
| Large tracked files | 10 | WARN |

Warnings reduce the score but do not make the command fail.

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Analysis completed with no FAIL result; WARN is allowed. |
| 1 | Analysis completed and at least one check returned FAIL. |
| 2 | Invalid usage, option, or repository path. |
| 3 | Git execution or unexpected runtime failure. |

## Architecture and tests

The application uses a one-way, presentation-independent analysis pipeline; see
[docs/architecture.md](docs/architecture.md). Run the offline suite with:

```bash
python -m pytest
```

GitHub Actions tests Python 3.11 and 3.13 on Linux and Windows.

## Security and privacy

The analyzer is read-only: it never edits files, runs project tests, changes Git
state, contacts remotes, or sends data externally. Git commands are exact
allowlisted argument sequences with `shell=False`, disabled prompts, and a
timeout. Findings show paths and risk categories, never secret contents. See
[SECURITY.md](SECURITY.md).

## Known limitations and roadmap

- v1 analyzes local non-bare Git working trees only.
- CI checks confirm workflow files exist; they do not interpret workflow logic.
- Test checks detect structure; they do not execute the analyzed tests.
- Secret detection is filename/path based, not content scanning.
- Automatic fixes and GitHub API integration are outside v1 scope.

Future versions may add opt-in deeper configuration analysis while preserving
the read-only and local-first security model.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under the [MIT License](LICENSE).
