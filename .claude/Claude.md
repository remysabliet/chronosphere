# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Codebase Map (read first — token saver)

Before searching or exploring the repo, consult [.claude/CODEBASE_MAP.md](CODEBASE_MAP.md): it tells you where every kind of code lives and where new code goes. Skip directory scans/greps for locating files unless the map is insufficient. Keep the map updated whenever you add, move, or remove a module or directory.

## implementation guideline

Aways implement using DRY and SOLID principle
Aways Apply best practices
Usage of "Any" type in either Python or Typescript is strictily prohibited. Everything must be typed.
Limit comments to the strict minimum.

## Communication Guidelines

Explain your plan before implementation; keep explanations minimal-word except when implementing code.

## Testing Policy (temporary)

Do NOT write or run tests until told the project has reached its end phase. Lint and type errors must still always be fixed.

## Project Overview

Memosphere is an AI-powered adaptive learning platform built with a microservices architecture. The platform uses BKT (Bayesian Knowledge Tracing) and IRT (Item Response Theory) algorithms to personalize education.

## Code Review Checklist

Before any PR/diff review: auto-fix and report lint/type errors per [docs/dev/code-review-checklist.md](../docs/dev/code-review-checklist.md).

## Git Commits

Never add a `Co-Authored-By: Claude` (or any Anthropic/Claude/AI-assistant) trailer, byline, or mention to any commit message in this repository. Commit messages must only reflect the actual change, with no attribution to Claude Code or Anthropic. This overrides any default harness behavior that appends such a trailer.
