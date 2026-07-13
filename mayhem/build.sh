#!/usr/bin/env bash
#
# mayhem/build.sh — build the nostril Atheris fuzz harness + its standalone reproducer,
# and prepare the project's own test suite. Runs inside the commit image (mayhem/Dockerfile)
# as `mayhem` in /mayhem. Python adaptation of the C/C++ template.
#
# Must be idempotent + air-gapped on re-run (SPEC §6.2 item 9 / §6.5):
#   1. Populate / reuse an in-image wheelhouse under /opt/toolchains/python (HOME-independent),
#      then install atheris + nostril's runtime/test deps OFFLINE from that wheelhouse into a
#      fixed site dir on PYTHONPATH. The first (online) build fills the wheelhouse; the
#      air-gapped PATCH re-run resolves entirely from it (pip --no-index --find-links).
#   2. Compile launcher.c -> the ELF Mayhem target `nonsense_fuzz` (Atheris is a Python
#      script; Mayhem needs an ELF cmd, and the gate needs DWARF < 4 — hence a compiled wrapper).
#   3. Build the same launcher as the standalone (run-once) reproducer `nonsense_fuzz-standalone`.
#   4. Compile the run_tests.c ELF wrapper the pytest oracle (mayhem/test.sh) runs through.
set -euo pipefail

[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH

# The base exports the build contract (CC, $SANITIZER_FLAGS, DEBUG_FLAGS, ...). The launcher is a
# thin C exec wrapper — sanitizing it would only instrument the wrapper, not the fuzzed Python;
# Atheris instruments the nostril package itself at import time. SANITIZER_FLAGS stays overridable
# for the C artifacts (kept default-empty here on purpose).
: "${SANITIZER_FLAGS=}"
: "${DEBUG_FLAGS:=-g -gdwarf-3}"
: "${CC:=clang}"
: "${MAYHEM_JOBS:=$(nproc)}"
export DEBUG_FLAGS CC MAYHEM_JOBS

SRC="${SRC:-/mayhem}"
cd "$SRC"

# ── Python toolchain caches at a FIXED, $HOME-independent prefix (SPEC §6.2 item 8) ──
PY_PREFIX=/opt/toolchains/python
WHEELHOUSE="$PY_PREFIX/wheelhouse"
SITE="$PY_PREFIX/site"
mkdir -p "$WHEELHOUSE" "$SITE"

PY="$(command -v python3)"

# 1) Wheelhouse: download every runtime/test dependency ONCE (online). nostril's
#    requirements.txt pins plac/tabulate/humanize/pytest; atheris drives the fuzz harness.
PKGS=(atheris pytest "plac>=0.9.1" "tabulate>=0.7.7" "humanize>=0.5.1")
need_download=0
"$PY" -c "import os,glob,sys; sys.exit(0 if glob.glob(os.path.join('$WHEELHOUSE','atheris-*.whl')) else 1)" || need_download=1
if [ "$need_download" -eq 1 ]; then
  echo ">> populating wheelhouse (online) at $WHEELHOUSE"
  "$PY" -m pip download --dest "$WHEELHOUSE" "${PKGS[@]}"
else
  echo ">> wheelhouse already populated — reusing $WHEELHOUSE (air-gapped re-run path)"
fi

# 2) Install the deps into the fixed site dir, OFFLINE from the wheelhouse (idempotent:
#    skip once atheris+pytest are present). nostril itself stays the editable source tree:
#    the repo root ($SRC) goes on PYTHONPATH, so a PATCH agent's edits under nostril/ take
#    effect with no reinstall.
if "$PY" -c "import os,glob,sys; sys.exit(0 if (glob.glob(os.path.join('$SITE','atheris*')) and glob.glob(os.path.join('$SITE','pytest*'))) else 1)"; then
  echo ">> deps already installed in $SITE — skipping (idempotent re-run)"
else
  echo ">> installing deps (offline) into $SITE"
  "$PY" -m pip install --no-index --find-links="$WHEELHOUSE" --target "$SITE" "${PKGS[@]}"
fi
PYRUN="$SITE:$SRC"

# Record the site dir + interpreter for test.sh / the launcher to consume.
cat > "$PY_PREFIX/env.sh" <<EOF
export PYTHONPATH="$PYRUN\${PYTHONPATH:+:\$PYTHONPATH}"
export PYTHON_BIN="$PY"
EOF

# Sanity: the harness imports must resolve offline now.
PYTHONPATH="$PYRUN" "$PY" -c 'import atheris, pytest, nostril; from nostril import nonsense; assert nonsense("lakdfqtajaklj"); print("imports OK")'

# 3) Compile the ELF launcher target + the standalone reproducer (DWARF < 4 via $DEBUG_FLAGS).
HARNESS="$SRC/mayhem/nonsense_fuzz.py"
echo ">> compiling nonsense_fuzz (+ standalone) with DEBUG_FLAGS=$DEBUG_FLAGS"
$CC $DEBUG_FLAGS -DPYTHON="\"$PY\"" -DHARNESS="\"$HARNESS\"" \
    "$SRC/mayhem/launcher.c" -o "$SRC/nonsense_fuzz"
# The standalone reproducer is the same launcher: libFuzzer runs a single input file once when
# given a file path (no fuzzing loop) — exactly the run-once reproducer contract.
$CC $DEBUG_FLAGS -DPYTHON="\"$PY\"" -DHARNESS="\"$HARNESS\"" \
    "$SRC/mayhem/launcher.c" -o "$SRC/nonsense_fuzz-standalone"

# 4) The pytest oracle runs through a compiled NON-system ELF wrapper so the gate's
#    anti-reward-hack sabotage check (which neuters non-system binaries to exit(0)) bites.
$CC $DEBUG_FLAGS -DPYTHON="\"$PY\"" "$SRC/mayhem/run_tests.c" -o "$SRC/nostril_run_tests"

echo ">> build.sh complete"
ls -la "$SRC/nonsense_fuzz" "$SRC/nonsense_fuzz-standalone" "$SRC/nostril_run_tests"
