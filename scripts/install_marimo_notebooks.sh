#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <output_dir>"
    echo "  output_dir: directory to store the rendered notebooks"
    exit 1
fi

output_dir=${1:-public}/marimo

# create a temp directory to store the rendered notebooks
mytmpdir=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir')


if [ -d $output_dir ]; then
    echo "Output directory already exists. Clearing it."
    rm -rf $output_dir
else
    mkdir -p $output_dir
fi

for notebook in "marimo/*.py"; do
    # uv run marimo export html-wasm $notebook -o $mytmpdir/$(basename $notebook)
    # remove .py ending
    dir_name=$(basename $notebook)
    dir_name="${dir_name%.*}"
    echo -ne 'Y' | uv run marimo export html-wasm --sandbox --mode run $notebook -o $mytmpdir/$dir_name
    mv $mytmpdir/$dir_name ${output_dir}/$dir_name
done


trap "rm -rf $mytmpdir" EXIT SIGINT SIGTERM SIGQUIT SIGKILL