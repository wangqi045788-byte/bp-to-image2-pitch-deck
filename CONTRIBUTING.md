# Contributing

Contributions should improve evidence control, narrative selection, brand fidelity, Image2 prompt quality, or deterministic QA without weakening confidentiality boundaries.

Before submitting a change:

1. use only synthetic or independently public, rights-reviewed examples;
2. run `python -m unittest discover -s tests -v`;
3. run the Skill validator;
4. run `python scripts/public_release_check.py .` with any organization-specific denylist stored outside the repository;
5. confirm that no private job file or generated customer asset is present in the diff or history.

Do not submit real client prompts or sanitized examples derived from private engagements.
