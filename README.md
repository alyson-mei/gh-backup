# GitHub Backup Tool

Keeps local folders backed up to GitHub. You list folders and repo names in
a config file, and the tool commits and pushes on a schedule so there's
always an off-machine copy. Design and requirements by me, with code written by Claude.

Example config:

```yaml
github_profile: alyson-mei

repos:
  - repo_name: backup-repo-1
    local_path: /home/alyson/PyProjects/for_tests/repo_1
    visibility: private

  - repo_name: backup-repo-2
    local_path: /home/alyson/PyProjects/for_tests/repo_2
    visibility: public

schedule:
  interval_minutes: 60
```

With this config, both folders get turned into git repos (GitHub repos get
created too, if they don't exist yet), and every 60 minutes any local
changes are committed and pushed.

**Status:** MVP, still testing. Runs from a terminal on Linux only for now.

## Setup

### 1. Prerequisites (any OS)

- Python 3.10+
- git, installed and on PATH
- A GitHub token

For the token: GitHub → Settings → Developer settings → Personal access
tokens → Fine-grained tokens → Generate new token.

Permissions:

- **Repository access**: with the default auto-create behavior, pick "All
  repositories" (a fine-grained token can't be scoped to a repo that
  doesn't exist yet). If you'd rather create the repos yourself on GitHub
  first, scope it to "Only select repositories" and skip the permission
  below.
- **Contents**: Read and write. This is what push/pull actually need.
- **Administration**: Read and write. Only needed for auto-creating repos.

Everything else: no access.

### 2. Linux setup

From the project root:

```bash
make setup
```

Sets up a venv, installs the two dependencies, and creates a starter
`config.yaml` and `.env` if you don't have them yet.

Fill in `.env`:

```
GITHUB_TOKEN=ghp_xxxxxxxx
```

And `config.yaml`, listing the folders to back up (see the example above).

Then:

```bash
make run
```

## Usage

### What each run does

For every repo in `config.yaml`:

1. **Init** — make sure `local_path` is a git repo, creating one if not.
   Make sure `origin` is set, creating the GitHub repo first if needed.
2. **Commit** — stage and commit local changes. Skip if there's nothing to
   commit.
3. **Pull** — pull from GitHub before pushing, so changes from another
   machine don't get overwritten.
4. **Push**.

Real conflicts on pull aren't auto-resolved. The tool logs it and skips
that repo for the run — sort it out by hand and it'll pick back up next
time. This assumes you're working from one machine at a time.

If one repo fails (bad network, permissions, whatever), it's logged and the
rest still run.

### Running

`make run` loops: run the pipeline for all repos, sleep for
`interval_minutes`, repeat. `Ctrl+C` stops it after the current repo
finishes, not mid-push.

For testing individual steps:

```bash
make init      # init step only, all repos
make commit    # commit only
make push      # pull + push only
```

`make clear` wipes everything back to a clean slate: deletes the GitHub
repos and the local `.git` folders. Useful when you're iterating on the
config.

`make clean` is unrelated — removes the venv, logs, and `__pycache__`.

### Logs

Logged to console and to `gh_backup.log` in the project root. Rotates at
~1 MB, keeps 3 old copies (roughly 4 MB total on disk).