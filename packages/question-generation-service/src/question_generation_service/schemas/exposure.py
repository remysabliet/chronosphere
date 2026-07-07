from pydantic import BaseModel

from memosphere_domain import ExposureLevel


class ExposureRequest(BaseModel):
    exposure_level: ExposureLevel


class ExposureResult(BaseModel):
    thema: str
    exposure_level: ExposureLevel
    p_l0: float
    concepts_initialized: int
