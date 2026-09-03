# Confidentiality boundary

Treat every user file, pasted fact, prompt, generated prompt, intermediate image, and output as private unless it is clearly public or the user explicitly classifies it otherwise.

## Isolation rule

- Create each job outside the installed skill or cloned repository.
- Keep raw inputs under the job directory. Never copy them into `examples/`, `assets/`, tests, documentation, logs, or Git history.
- Do not use real client names, transaction names, people, figures, screenshots, file paths, logos, or stylistic fingerprints in public examples.
- Do not quote an internal template. Convert only the general decision rule into public guidance.
- Keep public and private modes separate. A sanitized prompt is still private unless independently reviewed for release.

## Source labels

Use one of:

- `private`: internal or client material;
- `public`: publicly accessible and suitable for the current use;
- `third_party`: externally sourced with license or attribution considerations;
- `user_provided`: provenance known only from the user;
- `synthetic`: created only for testing or demonstration.

The label controls storage and release, not truthfulness. A public source can still be wrong; a private source can still be authoritative.

## Public repository gate

A repository is not ready for public release until all of these are true:

- only code, generic instructions, and synthetic or explicitly public examples remain;
- absolute paths, usernames, email addresses, secrets, source binaries, raw prompts, generated customer assets, caches, and archives are absent;
- the release scanner passes on the worktree and Git history;
- company ownership, compliance, branding, and third-party-license review are complete where applicable;
- the release is built from a new or audited clean history.

Use `scripts/public_release_check.py` with a private denylist stored outside the repository. Never commit the denylist itself.

## Stop conditions

Stop public-release work when provenance is uncertain, private material appears in history, or authorization is missing. Continue private deck production only within the authorized job directory.
