# Learning Engine Service

Core AI component implementing BKT and IRT algorithms for adaptive learning.

## Tech Stack
- **Python 3.11+ + FastAPI**
- **NumPy, SciPy** for ML algorithms
- **PostgreSQL** for model storage

## Key Features
- **BKT**: Bayesian Knowledge Tracing for mastery modeling
- **IRT**: Item Response Theory for ability estimation
- **Adaptive Decision Engine**: Intelligent question selection
- **Spaced Repetition**: Memory decay and reinforcement

## API Endpoints
```
POST /bkt/initialize      # Initialize BKT model
PUT  /bkt/update         # Update BKT parameters
GET  /bkt/mastery        # Get mastery probabilities
POST /adaptive/next-question # Get next question
POST /mastery/declare    # Declare mastery
```

## Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 3002
```

## Local Port: 3002