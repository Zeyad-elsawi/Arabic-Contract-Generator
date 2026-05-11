"""Pydantic models describing the structured contract and the critic output.

The drafter is constrained to emit JSON matching ``DraftedContract``. The
critic is constrained to emit JSON matching ``CritiqueReport``. Holding the
LLM to a schema is what makes per-article editing, version diffing and the
strict-review pipeline reliable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Contract structure
# ---------------------------------------------------------------------------
class Party(BaseModel):
    name: str = Field(..., description="الاسم الكامل للطرف")
    role: str = Field(..., description="صفة الطرف في العقد (بائع، مشتري، ...)")
    address: str = Field("", description="العنوان أو محل الإقامة")
    national_id: str = Field("", description="الرقم القومي / السجل التجاري")
    representative: str = Field("", description="صفة الممثل إن وجد")


class Article(BaseModel):
    number: int = Field(..., description="رقم البند، يبدأ من 1")
    title: str = Field(..., description="عنوان البند")
    body: str = Field(..., description="نص البند بالكامل بصياغة قانونية مصرية")


class DraftedContract(BaseModel):
    title: str = Field(..., description="عنوان العقد الكامل")
    preamble: str = Field(..., description="ديباجة العقد: التاريخ والمكان وما إلى ذلك")
    parties: list[Party] = Field(..., min_length=2)
    recitals: list[str] = Field(
        default_factory=list,
        description="حيثيات (Whereas clauses) إن وجدت",
    )
    subject: str = Field(..., description="محل العقد ومحدداته")
    articles: list[Article] = Field(..., min_length=4)
    governing_law: str = Field(..., description="القانون الحاكم والمحكمة المختصة")
    signature_block: str = Field(
        default="حُرر هذا العقد من نسختين بيد كل طرف نسخة للعمل بها عند اللزوم.",
        description="نص ختام العقد قبل التوقيعات",
    )


# ---------------------------------------------------------------------------
# Critic output
# ---------------------------------------------------------------------------
Severity = Literal["critical", "high", "medium", "low"]


class RedFlag(BaseModel):
    article_number: int | None = Field(
        None,
        description="رقم البند المعني، أو null إذا كانت الملاحظة عامة",
    )
    severity: Severity = Field(..., description="درجة الخطورة")
    category: str = Field(
        ...,
        description=(
            "تصنيف الملاحظة، مثل: missing_clause, one_sided, vague, "
            "contradiction, civil_code_violation, formal_requirement"
        ),
    )
    issue: str = Field(..., description="وصف المشكلة بالعربية")
    suggested_fix: str = Field(..., description="اقتراح للتعديل بالعربية")
    civil_code_reference: str = Field(
        "",
        description="مرجع من القانون المدني المصري إن وجد",
    )


class CritiqueReport(BaseModel):
    overall_quality: Severity = Field(
        ...,
        description="تقييم عام للعقد ككل",
    )
    summary: str = Field(..., description="ملخص بالعربية لحالة العقد")
    red_flags: list[RedFlag] = Field(default_factory=list)
