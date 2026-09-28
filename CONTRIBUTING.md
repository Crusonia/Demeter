# Contributing to Demeter

Demeter grows through small, reviewable improvements to evidence, equations,
experiments, and explanations. Newcomers are welcome. A source, a clear question,
a competing hypothesis, or a confusing setup step can be as useful as code.
Start with [the project introduction](docs/START_HERE.md) and
[installation instructions](docs/GETTING_STARTED.md).

Participation follows the [code of conduct](CODE_OF_CONDUCT.md). Good-faith
challenges to the Food is Health thesis, null results, and competing explanations
are welcome; agreement with a preferred conclusion is never a review criterion.

## Choose a contribution

Use [issues](https://github.com/Crusonia/Demeter/issues/new/choose) for setup bugs,
questions, evidence, and scenario proposals. You do not need a finished solution.
For a new scientific mechanism, propose the decision/question, causal path,
supporting and conflicting evidence, and validation plan before building it.

For material model or evidence changes, use the **Scientific model or evidence
change** issue form and the [scientific RFC process](docs/rfcs/README.md).
The [scientific review rules](docs/SCIENTIFIC_REVIEW.md) explain which changes need
an RFC, the before/after evidence record, review responsibilities, and conflict
disclosures. Major architecture decisions also use the
[decision log](docs/decisions/README.md). Small corrections can use the PR record
when the review rules permit it; a question does not require a finished RFC.

Use the [model-design inputs](docs/design/README.md) to connect that proposal to
the relevant loop/pathway, externality, input-package, and formulation/test IDs.
Include those references in the issue/PR and link actual evidence keys and code
when implemented. The registers hold premises and design requirements; they do
not authorize later-phase code or replace the parameter registry.

The current priority is the [v0.1 health acceptance gate](docs/V0_1_STATUS.md).
Future agriculture, behavior, economics, and policy ideas belong in the roadmap
and issue discussion until that gate is met. This preserves the larger ambition
while keeping each implementation testable. Read [AGENTS.md](AGENTS.md),
[the program vision](docs/PROJECT_VISION.md), and the
[current objective](docs/CODEX_V0_1_OBJECTIVE.md) before changing model behavior.

## Documentation changes without installing anything

On GitHub, open the document and select the pencil icon to edit. GitHub will guide
you through making a fork or branch and proposing a pull request. Describe what
was unclear and how the edit helps. For a question alone, open an issue instead.

## Code, data, or larger documentation changes

A **fork** is your copy of the project on GitHub. A **branch** holds one proposed
change. A **pull request (PR)** asks the maintainer to review it for inclusion.

1. Select **Fork** on [Crusonia/Demeter](https://github.com/Crusonia/Demeter).
2. Clone your fork. Replace `YOUR-USERNAME` below with your GitHub username.

```text
git clone https://github.com/YOUR-USERNAME/Demeter.git
cd Demeter
git remote add upstream https://github.com/Crusonia/Demeter.git
git switch -c docs/clarify-first-run
uv sync --locked
```

Use a descriptive branch name for your task. If Git needs your commit identity,
set it for this checkout with `git config user.name "Your Name"` and
`git config user.email "YOUR-COMMIT-EMAIL"`. GitHub provides a private noreply
commit address in your account's email settings if you prefer.

3. Make a bounded change. Add tests for changed model behavior and meaningful
   failure modes; documentation-only changes do not need artificial tests.
4. Run the checks from the repository root:

```text
uv run demeter validate
uv run python -X utf8 -m pytest
uv run ruff check .
uv run python scripts/verify_source_archive.py --rebuild
uv run demeter data verify-packages --check-tracked
```

For rendering changes, also generate the report and inspect it; the CI browser
check runs on Linux. For data changes, follow [the data contribution policy](data/README.md).

5. Review and commit only your intended files. This example stages one document;
   substitute the actual files you changed.

```text
git status --short
git diff
git add docs/GETTING_STARTED.md
git diff --cached
git commit -m "Clarify first-run instructions"
git push -u origin HEAD
```

6. Open your fork on GitHub and choose **Compare & pull request**, with
   `Crusonia/Demeter:main` as the base. Fill in the PR template. Draft PRs are
   welcome when you want feedback before finishing.

If you use the optional [GitHub CLI](https://cli.github.com/), `gh auth login`
sets it up, and `gh pr create --repo Crusonia/Demeter --base main --web` opens the
same review flow. No GitHub CLI is needed to run Demeter.

Push subsequent commits to the same branch to update your PR. If `main` advances,
update with `git fetch upstream` and `git merge upstream/main`, resolve any
conflicts, rerun checks, and push. Ask for help if a conflict involves scientific
definitions you do not understand.

## Review and merge

Carter Williams ([@jcarterwil](https://github.com/jcarterwil)) is the maintainer
and designated merger. Contributors can propose changes and discuss reviews;
write access alone does not grant permission to merge into `main`. CODEOWNERS
requests Carter's review, while GitHub branch protection enforces the merge rule.

CI runs on every PR, including fork PRs, with read-only permissions and no project
secrets. GitHub may hold an outside contributor's first workflow run for maintainer
approval. Carter should inspect changes, especially workflow edits, before allowing
it to run. Passing CI demonstrates software checks, not scientific acceptance.

Scientific changes need traceable sources, explicit definitions/units, uncertainty,
and a record of what changed in validation. Review disagreement through testable
claims and competing evidence. Keep discussion respectful and avoid personal attacks.
See [governance](GOVERNANCE.md) for maintainer commands and the exact controls.

For material scientific changes, record software assessment, scientific review,
maintainer disposition, and permitted scientific use separately, using the PR
template. Disclose relevant funding, employment, advisory roles, equity interests,
or authorship of evidence being assessed, or state that no relevant conflicts are
known. Reviewers and maintainers disclose too. Pending domain review stays pending;
an engineering merge does not make a model scientifically accepted.

## Attribution and reuse

Project code is [MIT licensed](LICENSE). Submit code you are entitled to contribute
under those terms and retain attribution. Third-party datasets and articles keep
their original terms: an open repository does not make every source redistributable.
Include source credit and provenance; never include credentials, restricted records,
or identifiable personal health data. AI-assisted contributions receive the same
evidence and review requirements; verify all citations and results yourself.
