#!/bin/bash

# create a temp directory to store the rendered notebooks
mytmpdir=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir')

mkdir -p public/marimo

for notebook in "marimo/*.py"; do
    # uv run marimo export html-wasm $notebook -o $mytmpdir/$(basename $notebook)
    # remove .py ending
    dir_name=$(basename $notebook)
    dir_name="${dir_name%.*}"
    echo -ne 'Y' | uv run marimo export html-wasm --sandbox --mode run $notebook -o $mytmpdir/$dir_name
    mv $mytmpdir/$dir_name public/marimo/
done


trap "rm -rf $mytmpdir" EXIT SIGINT SIGTERM SIGQUIT SIGKILL