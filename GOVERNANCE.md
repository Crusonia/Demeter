# Community development and maintainer workflow

Demeter is open to contributions. Carter Williams
([@jcarterwil](https://github.com/jcarterwil)) owns the merge decision for
`Crusonia/Demeter`. Anyone can fork, open an issue, or propose a PR. Community
participation does not require repository write access.

## Merge policy

The intended live configuration is recorded in
[`.github/branch-protection.json`](.github/branch-protection.json):

| Control on `main` | Setting |
| --- | --- |
| Who may update/merge | `jcarterwil`; no other users, teams, or apps on the allowlist. |
| Contributor reviews | One approval and code-owner review; Carter owns all paths. Approvals become stale when the reviewed diff changes. |
| Carter's own PRs | Carter can bypass the PR review requirement, avoiding a self-approval deadlock. |
| Required checks | `test (3.11)`, `test (3.12)`, `test (macOS)`, `test (Windows)`, from GitHub Actions. |
| Branch freshness | Must be up to date with `main`. |
| Review conversations | Must be resolved. |
| Admin enforcement | Enabled; Carter's PR-review exception does not waive required checks. |
| Force push / deletion of `main` | Disabled. |

CODEOWNERS routes reviews; it does not itself protect a branch. The GitHub API
settings are what enforce access. Existing organization members may have write
access, but cannot merge into `main` under these restrictions. Repository/organization
administrators can change protection settings, so administrative access remains
trusted and should be reviewed when maintainers change.

The PR-review bypass is scoped by GitHub to an actor, not to PR authorship. Carter
can use it on any PR and could use it for direct updates that satisfy the other
checks. Project policy is to use PRs for all ordinary changes, including Carter's,
and record review before merging others' contributions. No bot auto-merges PRs.

## Carter: create and merge a PR

On a clean checkout of `main` (keep any unrelated work on its existing branch):

```text
git pull --ff-only
git switch -c docs/my-change
```

Make the change, run the [contributor checks](CONTRIBUTING.md), review the diff,
and stage the specific files. Then:

```text
git commit -m "Describe the change"
git push -u origin HEAD
gh pr create --repo Crusonia/Demeter --base main --web
```

To finish, substitute the PR number for `NUMBER`:

```text
gh pr checks NUMBER --repo Crusonia/Demeter --watch
gh pr view NUMBER --repo Crusonia/Demeter --web
gh pr merge NUMBER --repo Crusonia/Demeter --squash --delete-branch
```

For another contributor's PR, review its changes and record your approval first.
Your own PR does not need somebody else's approval. If the branch is behind,
update it and let CI rerun. Do not use `--admin` to get around failed checks.
The browser's **Squash and merge** button is an alternative to the last command.

## Reproduce or audit the GitHub settings

An administrator can apply the reviewed configuration from the repository root:

```text
gh api --method PUT repos/Crusonia/Demeter/branches/main/protection --input .github/branch-protection.json
gh api repos/Crusonia/Demeter/branches/main/protection
```

The first command changes live settings; the second is read-only. Changing the
JSON file alone does not update GitHub. Keep the required check names in sync with
the workflow. Apply a new check requirement only when the corresponding job exists
on the setup PR; otherwise other PRs may wait for a check they cannot produce.
GitHub's [protected branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
and [API reference](https://docs.github.com/en/rest/branches/branch-protection)
describe these controls.

## Scientific decisions and releases

The [program vision](docs/PROJECT_VISION.md) is the long-term direction. Current
implementation is bounded by [AGENTS.md](AGENTS.md) and the
[v0.1 acceptance status](docs/V0_1_STATUS.md). Changes to scientific meaning must
record evidence, assumptions, uncertainty, validation, and unresolved objections
in the repository and PR. Ask relevant domain contributors to review material
changes; maintainer merge authority is not a substitute for scientific expertise.

An engineering merge or tagged prerelease is not a declaration of scientific
readiness. A scientific release requires the documented acceptance criteria and
the scientific validation gate, with a reproducible source/data/model version.
Broader modules are added in stages as those gates are met.
