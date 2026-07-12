# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
