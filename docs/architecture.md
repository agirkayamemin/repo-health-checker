# Architecture

The application follows a small one-way pipeline:

1. `repository` canonicalizes input and resolves the Git working-tree root.
2. `git_client` enforces exact read-only Git command forms and timeouts.
3. `git_state` and `scanner` collect Git and filesystem facts.
4. `checks` and `hygiene` convert facts into typed results.
5. `scoring` builds the score and status counters.
6. `analyzer` returns one immutable `AnalysisReport`.
7. `reporters` render terminal or JSON output; `cli` maps exit codes.

Presentation code never runs Git or scans files. The scanner does not follow
symlinked directories and treats generated environment/cache/IDE directories as
opaque paths. Runtime code uses only the Python standard library.
