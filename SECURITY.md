# Security and confidentiality

Do not commit client materials, internal decks, raw prompts, source documents, generated customer visuals, private company names, personal information, credentials, absolute user paths, or confidential denylist terms.

Run private jobs outside this repository. Use a denylist stored outside the repository when running `scripts/public_release_check.py`.

If sensitive material appears in Git history, stop release work. Removing it from the latest commit is insufficient; rebuild or rewrite the affected history only with explicit authorization and complete review.

Report security concerns privately to the repository owner rather than opening a public issue containing sensitive content.
