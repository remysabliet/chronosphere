# Learning Engine Service

Core AI component implementing BKT and IRT algorithms for adaptive learning.

## Tech Stack

- **Python 3.13 + FastAPI** (Security updates until 2029)
- **NumPy, SciPy, scikit-learn** for ML algorithms
- **PostgreSQL** for model storage

## Key Features

- **BKT**: Bayesian Knowledge Tracing for mastery modeling (using `bkt` package v6.0.0)
- **IRT**: Item Response Theory for ability estimation (custom implementation)
- **Adaptive Decision Engine**: Intelligent question selection
- **Spaced Repetition**: Memory decay and reinforcement

---

## ⚠️ Important: IRT Implementation Note

### Why IRT is Implemented Manually

**Problem:** As of October 2025, there's a dependency incompatibility:

- The `bkt` package requires Python **≥ 3.12**
- ALL IRT packages on PyPI (py-irt, pyirt, etc.) require Python **< 3.12**

**Decision:** Use Python 3.13 (longest security support until 2029) with:

- ✅ `bkt` package for BKT algorithms
- ✅ Custom IRT implementation using NumPy/SciPy

### IRT Implementation Resources

IRT models (1PL, 2PL, 3PL) are well-documented and straightforward to implement:

- **1PL (Rasch Model)**: Single difficulty parameter
- **2PL**: Difficulty + discrimination parameters
- **3PL**: Difficulty + discrimination + guessing parameters

Recommended resources:

- [IRT Wikipedia](https://en.wikipedia.org/wiki/Item_response_theory)
- [NumPy/SciPy optimization](https://docs.scipy.org/doc/scipy/reference/optimize.html)
- Example implementations available in academic papers

### Future Consideration

Monitor PyPI for IRT packages supporting Python 3.13+:

```bash
# Check for updates
poetry show --outdated | grep irt
```

---

## API Endpoints

```
POST /bkt/initialize      # Initialize BKT model
PUT  /bkt/update         # Update BKT parameters
GET  /bkt/mastery        # Get mastery probabilities
POST /irt/estimate-ability # Estimate learner ability (IRT)
POST /irt/estimate-difficulty # Estimate item difficulty (IRT)
POST /adaptive/next-question # Get next question
POST /mastery/declare    # Declare mastery
```

## Development

### Using Poetry (Recommended)

```bash
cd packages/learning-engine-service
poetry install
poetry run uvicorn packages.learning_engine_service.main:app --reload --port 8002
```

### Using Docker

```bash
# From project root
docker-compose up learning-engine-service
```

### Check Dependencies Status

```bash
poetry show --outdated  # List outdated packages
poetry update          # Update to latest compatible versions
```

## Local Port: 8002
