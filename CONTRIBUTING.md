# Contributing

Thanks for taking a look at SheetFlow.

If you find a problem, open an issue and include a small example that shows what happened. Please use made-up data rather than sharing customer files or personal information.

For a code change:

1. Create a branch for the change.
2. Add or update a test for the behavior.
3. Install the development tools with \`pip install -e ".[dev]"\`.
4. Run \`ruff check .\` and \`pytest\`.
5. Open a pull request and explain what changed and why.

For changes that affect cleaning behavior, please mention whether the step can remove rows or change values. That makes it easier for someone reviewing the change to understand its effect on their data.
