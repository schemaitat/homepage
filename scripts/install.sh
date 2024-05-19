#!/bin/bash
rm -rf ${HOME}/bin
mkdir -p ${HOME}/bin
mkdir -p ${HOME}/poetry

# install quarto
export QUARTO_VERSION=1.4.554
curl -o quarto.tar.gz -L \
    "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"
tar -zxvf quarto.tar.gz \
    --strip-components=1 \
    -C ${HOME}
rm quarto.tar.gz

# install uv
export UV_RELEASE=0.1.44

curl -o uv.tar.gz -L \
    "https://github.com/astral-sh/uv/releases/download/${UV_RELEASE}/uv-x86_64-unknown-linux-gnu.tar.gz"
tar -zxvf uv.tar.gz \
    --strip-components=1 \
    -C ${HOME}/bin

rm uv.tar.gz

# install hugo
export HUGO_RELEASE=0.108.0

curl -o hugo.tar.gz -L \
    https://github.com/gohugoio/hugo/releases/download/v${HUGO_RELEASE}/hugo_extended_${HUGO_RELEASE}_Linux-64bit.tar.gz
tar -zxvf hugo.tar.gz -C ${HOME}/bin
rm hugo.tar.gz

# install poetry
curl -sSL https://install.python-poetry.org | POETRY_HOME=${HOME}/bin/poetry python3 -

# make all binaries executable
chmod -R +x ${HOME}/bin

