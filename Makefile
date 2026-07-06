SHELL := bash

all: help

help:
	@echo "mdlint     		- lint markdown"

mdlint:
	markdownlint-cli2 --config .markdownlint.yaml "**/*.md" "#node_modules" "#!.venv"  "#!.tox" --fix
