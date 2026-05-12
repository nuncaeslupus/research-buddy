# Releasing

Releases are automated via the **`v*` tag → PyPI + GitHub release** pipeline
in `.github/workflows/release.yml`.

## One-time setup (already done for `research-buddy` on PyPI)

PyPI's trusted publishing is configured so this repository's `release.yml`
workflow can upload without an API token. If you need to reconfigure (for a
fork, or after changing workflow filename / environment name), do this once:

1. Log into https://pypi.org as a project maintainer.
2. Open the project → **Manage → Publishing** → **Add a new pending publisher**
   (or **Trusted publisher** on an existing project).
3. Fill in:
   - PyPI project name: `research-buddy`
   - Owner: `nuncaeslupus`
   - Repository: `research-buddy`
   - Workflow filename: `release.yml`
   - Environment: `pypi`
4. Save.

## Cutting a release

From a clean `main`:

```bash
# 1. Bump the version and sync the four places it appears
vim pyproject.toml            # edit [project].version
make version-sync             # propagates to __init__.py, starter.json, README heading
make check-version-sync       # sanity check

# 2. Update CHANGELOG.md
#    - rename the [Unreleased] section to [X.Y.Z] — YYYY-MM-DD
#    - add a new empty [Unreleased] section on top (optional)

# 3. Commit the bump + changelog
git add -u && git commit -m "chore(release): bump to X.Y.Z"
git push

# 4. Tag the release commit on main and push the tag
git tag -a vX.Y.Z -m "Research Buddy vX.Y.Z"
git push origin vX.Y.Z
```

Pushing the tag triggers `.github/workflows/release.yml`:

1. **build** — verifies the tag matches `pyproject.toml.project.version`,
   runs `make check-version-sync`, builds the wheel + sdist, and runs
   `twine check`.
2. **publish-pypi** — uploads `dist/*` to PyPI via trusted publishing (no
   token needed). Gated behind the `pypi` GitHub environment so you can
   require manual approval if desired.
3. **github-release** — creates the GitHub release from the tag, uses
   `CHANGELOG.md` as the body, and attaches the built distributions.

## Do not also `make publish` locally

The workflow is the canonical publish path. `make publish` is a fallback for
when the workflow is unavailable. To prevent the two from racing, `make
publish` refuses when a `v<current-pyproject-version>` tag already exists on
`origin` (it would race the workflow and fail with a PyPI 400 "File already
exists" the moment whichever path uploads second). The guard's message
points at `make publish-force` for explicit bypass — use that only when the
workflow is genuinely broken and you know what you're doing.

This is why pushing a tag is sufficient; you do not need to run anything
locally after `git push origin vX.Y.Z`.

## Failure recovery

- **Tag ↔ version mismatch**: the `build` job fails early. Delete the tag
  locally and on origin (`git tag -d vX.Y.Z && git push origin :vX.Y.Z`),
  fix `pyproject.toml` + `make version-sync`, commit, and re-tag.
- **PyPI upload fails after build succeeded**: `dist/` artifacts are retained
  for 7 days on the build job. Re-run the `publish-pypi` job from the Actions
  UI.
- **PyPI version already exists**: PyPI refuses to overwrite a published
  version. Bump to the next patch (`X.Y.Z+1`) and repeat the release flow.
  Most common cause is the `make publish` / workflow race described above —
  the guard added in 1.9.x makes this hard to hit by accident.
- **Workflow's `publish-pypi` job failed but PyPI got the upload anyway**
  (race between local `make publish` and the workflow, the situation that
  motivated the guard): the workflow's `github-release` job is skipped as a
  downstream of the failed `publish-pypi`. Recover by running `gh release create vX.Y.Z --title 'vX.Y.Z — <title>' --notes-file <notes> dist/research_buddy-X.Y.Z-py3-none-any.whl dist/research_buddy-X.Y.Z.tar.gz` manually.

## What counts as each kind of bump

See `CHANGELOG.md` "Migration guidance for the future" and the semver table in
`README.md`'s "Version compatibility" section. Short version:

- **PATCH** (X.Y.**Z**) — bug fixes, refactors, doc-only changes. Silent for
  users with older documents.
- **MINOR** (X.**Y**.0) — backwards-compatible feature additions. Older docs
  build without action; agent bumps `meta.research_buddy_version` on next
  write.
- **MAJOR** (**X**.0.0) — breaking changes to the document schema or the
  `build` / `validate` output. Triggers the CLI's MAJOR-mismatch warning on
  older documents. Add a detailed **Upgrading from X-1.\*** section to
  `CHANGELOG.md`.
