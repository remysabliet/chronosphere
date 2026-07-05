from typing import Literal

from pydantic import BaseModel

ExposureLevel = Literal["Unseen", "Recognized", "Practiced", "Mastered"]

# Step 5 (main-workflow.md): flat starting P(L0) per self-reported exposure level,
# applied uniformly across every concept-Bloom pair until the placement probe
# and later BKT updates differentiate them.
EXPOSURE_TO_P_L0: dict[ExposureLevel, float] = {
    "Unseen": 0.2,
    "Recognized": 0.4,
    "Practiced": 0.6,
    "Mastered": 0.8,
}


class ExposureRequest(BaseModel):
    exposure_level: ExposureLevel


class ExposureResult(BaseModel):
    thema: str
    exposure_level: ExposureLevel
    p_l0: float
    concepts_initialized: int
