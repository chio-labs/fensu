# strata

Strata is an architecture linter for Python repos. It enforces which layers may
import which, what each module may contain, and whether functions stay small
and honest.

> Most linters catch bad code. Strata catches code that's in the wrong place,
> the wrong shape, or lying about what it does.

Status: design phase — not yet functional. Install name is `stratalint`
(the `strata` name on PyPI was taken); the CLI command is `strata`.

```
pip install stratalint
```
