from typing import Literal
from pydantic import BaseModel, Field

class Stock(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1, max_length=60)
    market: Literal["KOSPI", "KOSDAQ"]
    kind: Literal["관심", "보유"] = "관심"

class AnalyzeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    refresh: bool = False

class RegisterStock(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    kind: Literal["관심", "보유"] = "관심"

class Evidence(BaseModel):
    source_id: str
    quote: str = Field(min_length=10, max_length=360)

class Finding(BaseModel):
    article_id: str
    direction: Literal["상승 요인", "하락 요인", "판단 보류"]
    impact: Literal["높음", "중간", "낮음", "평가 불가"]
    reason: str = Field(max_length=700)
    counterpoint: str = Field(max_length=500)
    evidence: list[Evidence] = Field(max_length=4)

class Analysis(BaseModel):
    findings: list[Finding] = Field(max_length=20)

class ReviewItem(BaseModel):
    article_id: str
    reason_supported: bool = Field(default=True, description="설명의 사실·조건·시점·영향 범위가 원문에 부합하는가")
    counterpoint_supported: bool = Field(default=True, description="반대 근거의 사실·조건·영향 범위가 원문에 부합하는가")
    accepted: bool
    reason: str = Field(max_length=400)
    approved_impact: Literal["높음", "중간", "낮음"] | None = None

class Review(BaseModel):
    items: list[ReviewItem] = Field(max_length=5)

class EvidenceReference(BaseModel):
    source_index: int = Field(ge=0)
    chunk_index: int = Field(ge=0)

class GroundedFinding(BaseModel):
    article_index: int = Field(ge=0, le=4)
    evidence: list[EvidenceReference] = Field(max_length=3)
    direction: Literal["상승 요인", "하락 요인", "판단 보류"]
    impact: Literal["높음", "중간", "낮음", "평가 불가"]
    reason: str = Field(max_length=700)
    counterpoint: str = Field(max_length=500)

class GroundedAnalysis(BaseModel):
    findings: list[GroundedFinding] = Field(max_length=5)
