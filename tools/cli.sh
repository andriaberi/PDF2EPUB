#!/usr/bin/env bash
# Bookflow developer CLI, driven by the Makefile. Run `tools/cli.sh help` for usage.

set -uo pipefail
cd "$(dirname "$0")/.."

VENV=${VENV:-.venv}
PYTHON=${PYTHON:-$VENV/bin/python}
VERSION_FILE=src/bookflow/__init__.py

# Style

# Colour on a terminal or in GitHub Actions; NO_COLOR turns it off.
if [[ -z ${NO_COLOR:-} && ( -t 1 || -n ${GITHUB_ACTIONS:-} ) ]]; then
    BOLD=$'\e[1m' DIM=$'\e[2m' RESET=$'\e[0m'
    ACCENT=$'\e[36m' GREEN=$'\e[32m' RED=$'\e[31m' YELLOW=$'\e[33m'
    export FORCE_COLOR=1
else
    BOLD='' DIM='' RESET='' ACCENT='' GREEN='' RED='' YELLOW=''
fi

# ok/fail LABEL [DETAIL] — one status line: mark, label, dimmed detail.
line() {
    if [[ -n ${3:-} ]]; then
        printf '%s %-12s %s%s%s\n' "$1" "$2" "$DIM" "$3" "$RESET"
    else
        printf '%s %s\n' "$1" "$2"
    fi
}
ok()   { line "$GREEN✓$RESET" "$@"; }
fail() { line "$RED✗$RESET" "$@" >&2; }

strip_colour() { sed $'s/\e\\[[0-9;]*m//g' "$@"; }

# Steps

# spin LABEL CMD... — runs CMD quietly behind a spinner, leaving its output in
# $LOG (the caller removes it) and returning its status.
spin() {
    local label=$1; shift
    local pid
    LOG=$(mktemp)

    "$@" >"$LOG" 2>&1 &
    pid=$!
    trap 'kill $pid 2>/dev/null; printf "\r\e[K\e[?25h"; rm -f "$LOG"; exit 130' INT TERM

    if [[ -t 1 ]]; then
        local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) i=0
        printf '\e[?25l'
        while kill -0 "$pid" 2>/dev/null; do
            printf '\r%s%s%s %s' "$ACCENT" "${frames[i++ % 10]}" "$RESET" "$label"
            sleep 0.08
        done
        printf '\r\e[K\e[?25h'
    fi

    wait "$pid"
    local status=$?
    trap 'exit 130' INT TERM
    return "$status"
}

# step LABEL CMD... — runs CMD behind a spinner. On success prints the last line
# of its output (e.g. "All checks passed!"); on failure, the whole log.
step() {
    local label=$1; shift
    local status detail
    spin "$label" "$@"; status=$?

    if (( status == 0 )); then
        detail=$(strip_colour "$LOG" | grep . | tail -n1)
        ok "$label" "$detail"
    else
        fail "$label"
        printf '\n' >&2
        cat "$LOG" >&2
        printf '\n' >&2
    fi
    rm -f "$LOG"
    return "$status"
}

# pytest_step [ARG...] — runs pytest behind a spinner and lists every test
# under its file. On failure, pytest's failure report follows the list.
pytest_step() {
    local status plain summary
    spin pytest "$PYTHON" -m pytest -v --no-header "$@"; status=$?
    plain=$(strip_colour "$LOG")
    rm -f "$LOG"

    # "tests/test_x.py::test_y PASSED  [ 50%]" → a ✓/✗/• line under its file.
    printf '%s\n' "$plain" | awk -v G="$GREEN" -v R="$RED" -v Y="$YELLOW" -v D="$DIM" -v X="$RESET" '
        # A file that fails to import shows up only in the short summary.
        /^ERROR [^ :]+\.py( |$)/ {
            file = $2
            if (!(file in count)) { order[++files] = file; count[file] = 0 }
            failed[file] = 1
            line[file, ++count[file]] = "  " R "✗" X " " D "could not be imported" X
            next
        }
        /^[^ _=]/ && index($0, "::") && match($0, / (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)( |$)/) {
            id = substr($0, 1, RSTART - 1)
            result = substr($0, RSTART + 1, RLENGTH - 1); sub(/ $/, "", result)
            sep = index(id, "::"); file = substr(id, 1, sep - 1); name = substr(id, sep + 2)
            if (!(file in count)) order[++files] = file
            n = ++count[file]
            if (result == "PASSED" || result == "XFAIL") mark = G "✓" X
            else if (result == "SKIPPED") mark = Y "•" X
            else { mark = R "✗" X; failed[file] = 1 }
            note = (result == "PASSED" || result == "FAILED") ? "" : " " D tolower(result) X
            line[file, n] = "  " mark " " name note
        }
        END {
            for (f = 1; f <= files; f++) {
                file = order[f]
                printf "%s %s\n", (file in failed) ? R "✗" X : G "✓" X, file
                for (n = 1; n <= count[file]; n++) print line[file, n]
            }
        }'

    summary=$(printf '%s\n' "$plain" | grep -E '^=+ .+ =+$' | tail -n1 | sed -E 's/^=+ //; s/ =+$//')
    if (( status == 0 )); then
        ok pytest "$summary"
    else
        printf '\n' >&2
        printf '%s\n' "$plain" | awk '
            /^=+ (FAILURES|ERRORS) =+$/ { show = 1; next }
            /^=+ (short test summary info|warnings summary) =+$/ || /^=+ .* in [0-9.]+s/ { show = 0 }
            show' >&2
        printf '\n' >&2
        fail pytest "${summary:-exit status $status}"
    fi
    return "$status"
}

need_venv() {
    if [[ ! -x $PYTHON ]] && ! command -v "$PYTHON" >/dev/null; then
        fail "$PYTHON not found — run make install"
        exit 1
    fi
}

current_version() { sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE"; }

# Commands

cmd_help() {
    local A=$ACCENT R=$RESET B=$BOLD D=$DIM
    cat <<EOF
${B}Bookflow${R} ${D}— make <command>${R}

${B}Setup${R}
  ${A}install${R}     Create $VENV and install Bookflow with its dev tools

${B}Develop${R}
  ${A}format${R}      Format code and fix what can be fixed
  ${A}lint${R}        Check formatting and lint rules
  ${A}typecheck${R}   Type-check with mypy
  ${A}test${R}        Run the tests
  ${A}cov${R}         Run the tests with a coverage report
  ${A}check${R}       Lint, type-check and test (what CI runs)

${B}Version${R}
  ${A}version${R}     Print the current version
  ${A}bump${R}        Bump the version                   ${D}make bump TO=patch|minor|major|1.2.3${R}

${B}Dependencies${R}
  ${A}outdated${R}    List packages with newer releases
  ${A}upgrade${R}     Upgrade dependencies and pre-commit hooks

${B}Release${R}
  ${A}build${R}       Build the package into dist/
  ${A}clean${R}       Remove build files and caches

${D}Run Bookflow: python src book.pdf [options]${R}
EOF
}

cmd_install() {
    if [[ ! -x $PYTHON ]]; then
        step venv python3 -m venv "$VENV" || exit 1
    fi
    step pip "$PYTHON" -m pip install -q --upgrade pip || exit 1
    step dependencies "$PYTHON" -m pip install -q -e . --group dev || exit 1
    step "git hooks" "$VENV/bin/pre-commit" install || exit 1
}

cmd_format() {
    need_venv
    step "ruff format" "$PYTHON" -m ruff format . || exit 1
    step "ruff fix" "$PYTHON" -m ruff check --fix . || exit 1
}

cmd_lint() {
    need_venv
    local status=0
    step "ruff format" "$PYTHON" -m ruff format --check . || status=1
    step "ruff check" "$PYTHON" -m ruff check . || status=1
    return "$status"
}

cmd_typecheck() { need_venv; step mypy "$PYTHON" -m mypy; }

cmd_test() { need_venv; pytest_step; }

cmd_cov() {
    need_venv
    pytest_step --cov --cov-report= || exit 1
    printf '\n'
    "$PYTHON" -m coverage report
}

cmd_check() {
    local status=0
    cmd_lint || status=1
    cmd_typecheck || status=1
    cmd_test || status=1
    printf '\n'
    if (( status == 0 )); then
        printf '%s%sAll checks passed.%s\n' "$GREEN" "$BOLD" "$RESET"
    else
        printf '%s%sChecks failed.%s\n' "$RED" "$BOLD" "$RESET"
    fi
    return "$status"
}

cmd_version() { current_version; }

cmd_bump() {
    local to=${1:-patch} old new major minor patch
    old=$(current_version)
    if [[ ! $old =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        fail "No X.Y.Z __version__ in $VERSION_FILE"; exit 1
    fi
    IFS=. read -r major minor patch <<<"$old"
    case $to in
        major) new="$((major + 1)).0.0" ;;
        minor) new="$major.$((minor + 1)).0" ;;
        patch) new="$major.$minor.$((patch + 1))" ;;
        *)
            if [[ ! $to =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                fail "TO must be patch, minor, major or X.Y.Z, got '$to'"; exit 1
            fi
            new=$to ;;
    esac
    sed "s/^__version__ = .*/__version__ = \"$new\"/" "$VERSION_FILE" >"$VERSION_FILE.tmp" \
        && mv "$VERSION_FILE.tmp" "$VERSION_FILE"
    ok version "$old → $new"
}

cmd_outdated() {
    need_venv
    local out
    out=$("$PYTHON" -m pip list --outdated --exclude-editable 2>&1) || { fail outdated; printf '%s\n' "$out" >&2; exit 1; }
    if [[ -z $out ]]; then ok outdated "Everything is up to date"; else printf '%s\n' "$out"; fi
}

cmd_upgrade() {
    need_venv
    step dependencies "$PYTHON" -m pip install -q --upgrade --upgrade-strategy eager -e . --group dev || exit 1
    step "git hooks" "$VENV/bin/pre-commit" autoupdate || exit 1
}

cmd_build() {
    need_venv
    cmd_clean >/dev/null
    step build "$PYTHON" -m build -q
}

cmd_clean() {
    rm -rf build dist src/*.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
    find . -type d -name __pycache__ -not -path "./$VENV/*" -exec rm -rf {} +
    ok clean "Removed build files and caches"
}

case ${1:-help} in
    help|install|format|lint|typecheck|test|cov|check|version|bump|outdated|upgrade|build|clean)
        cmd=$1; shift; "cmd_$cmd" "$@" ;;
    *) fail "Unknown command '$1'"; printf '\n' >&2; cmd_help >&2; exit 1 ;;
esac
