# Contributing

Use Python 3.11 or newer and Git. Create a virtual environment, then install the
editable development package:

```bash
python -m pip install --editable ".[dev]"
python -m pytest
```

Open a focused issue before substantial work. Create a descriptive branch from
an up-to-date `main`, keep commits small and use Conventional Commits. Pull
requests must explain their purpose, tests, limitations, and linked issue.

Tests must use temporary repositories, avoid network access, and never modify a
real user repository. Do not include credentials, repository file contents, or
remote URLs in fixtures, logs, exceptions, issues, or pull requests.
