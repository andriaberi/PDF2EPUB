# Thin wrapper around tools/cli.sh, which does the work. Run `make` for usage.

# Recipes are indented with spaces instead of tabs (GNU Make >= 3.82).
empty :=
.RECIPEPREFIX := $(empty) $(empty)

.DEFAULT_GOAL := help
.PHONY: help install format lint typecheck test cov check version bump outdated upgrade build clean

# `make bump TO=patch|minor|major|1.2.3` (TO defaults to patch).
bump:
    @bash tools/cli.sh bump $(TO)

help install format lint typecheck test cov check version outdated upgrade build clean:
    @bash tools/cli.sh $@
