# Security

Repo Health Checker analyzes local repositories without modifying them. It does
not run project code or tests, contact remotes, scan file contents for secrets,
or send repository data to external services. Sensitive-file findings contain
paths and risk categories only.

Do not include real credentials or private repository data in a public report.
Report vulnerabilities privately through GitHub's security reporting feature
when available. Rotate any credential that may have been committed, even after
removing the file from the current tree.
