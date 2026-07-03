# memosphere-shared-auth

Shared Cognito JWT verification library for Memosphere Python services.

## Usage

Install as a local dependency in another service's `pyproject.toml`:

```toml
[tool.uv.sources]
memosphere-shared-auth = { path = "../shared-python" }
```

Then use in a FastAPI service:

```python
from memosphere_auth import CognitoTokenVerifier

verifier = CognitoTokenVerifier(issuer=COGNITO_ISSUER, audience=COGNITO_CLIENT_ID)

# Use as a FastAPI dependency
CurrentUser = Annotated[dict, Depends(verifier)]
```

## Testing

Uses `uv`.

```bash
# Install dev dependencies (first time)
uv sync --dev

# Run tests
uv run pytest tests/

# With coverage report (fails if < 80%)
uv run pytest tests/ --cov=memosphere_auth --cov-report=term-missing --cov-fail-under=80
```
