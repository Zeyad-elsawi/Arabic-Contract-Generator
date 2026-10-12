"""Central configuration: paths, model IDs, runtime constants.

Keep magic strings out of the rest of the codebase. If a model name changes
on the Groq side, edit it here only.
"""

from __future__ import annotations

import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent
TEMPLATES_DIR: Path = ROOT_DIR / "نماذج عقود" / "مصري - Copy"
VECTOR_DB_DIR: Path = ROOT_DIR / "vector_db"
GENERATED_DIR: Path = ROOT_DIR / "generated"

VECTOR_DB_DIR.mkdir(exist_ok=True)
GENERATED_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# Groq model IDs
# -----------------------------------------------------------------------------
DRAFTER_MODEL: str = "llama-3.3-70b-versatile"
CRITIC_MODEL: str = "llama-3.3-70b-versatile"
REFINER_MODEL: str = "llama-3.3-70b-versatile"
WHISPER_MODEL: str = "whisper-large-v3"

# Fallback fast model
FAST_MODEL: str = "llama-3.1-8b-instant"

# Optional premium polishing pass (Gemini). Only used if GEMINI_API_KEY is set.
GEMINI_MODEL: str = "gemini-2.5-pro"

# -----------------------------------------------------------------------------
# Generation params
# -----------------------------------------------------------------------------
DRAFTER_MAX_TOKENS: int = 8000
CRITIC_MAX_TOKENS: int = 3000
REFINER_MAX_TOKENS: int = 4000
DRAFTER_TEMPERATURE: float = 0.3
CRITIC_TEMPERATURE: float = 0.1
REFINER_TEMPERATURE: float = 0.2

# -----------------------------------------------------------------------------
# RAG
# -----------------------------------------------------------------------------
EMBEDDING_MODEL: str = "BAAI/bge-m3"   # multilingual, strong Arabic support
EMBEDDING_DIM: int = 1024
CHUNK_SIZE_TOKENS: int = 800           # ~ characters before splitting
CHUNK_OVERLAP_TOKENS: int = 150
RETRIEVAL_TOP_K: int = 8
INDEX_FILE: Path = VECTOR_DB_DIR / "egyptian_contracts.faiss"
META_FILE: Path = VECTOR_DB_DIR / "egyptian_contracts.meta.json"

# -----------------------------------------------------------------------------
# Contract categories -> template files
# -----------------------------------------------------------------------------
CONTRACT_CATEGORIES: dict[str, list[str]] = {
    "عقود البيع": [
        "عقد بيع عقار.docx",
        "عقد بيع محل تجاري.docx",
        "عقد بيع شقة.docx",
        "عقد بيع سيارة.docx",
        "عقد بيع ابتدائي.docx",
        "عقد بيع ابتدائي لأرض زراعية.docx",
        "عقد بيع ابتدائي مع حق امتياز لحين سداد كامل الثمن.docx",
        "عقد بيع حصة في تركة.docx",
        "عقد بيع حق رقبة مع الاحتفاظ بحق الانتفاع.docx",
        "عقد بيع سيارة مع احتفاظ البائع بالملكية حتى سداد الثمن.docx",
        "عقد بيع (بشرط مانع من التصرف).docx",
        "عقد بيع مع حق امتياز حتى سداد الثمن.docx",
        "عقد رسمي ببيع سفينة.docx",
        "عقد-بيع-أسهم-لشركة-قائمة.doc",
        "عقد-بيع-أسهم-لمشركة-تحت-التأسيس.doc",
        "عقد-بيع-ابتدائي-وارد-على-عمارة-.doc",
        "عقد-بيع-ارض-فضاء-خالية.doc",
        "عقد-بيع-ارض-معدة-للبناء.doc",
        "عقد-بيع-براءة-اختراع.doc",
        "عقد-بيع-بشرط-التجربة.doc",
        "عقد-بيع-بشرط-التنازل-للغير.doc",
        "عقد-بيع-حق-تأليف-1.doc",
        "عقد-بيع-حق-متنازع-فيه5-1.doc",
        "عقد-بيع-رسم-أو-نموذج-صناعي-1.doc",
        "عقد-بيع-عيادة-طبيب.doc",
        "عقد-بيع-مع-الاحتفاظ-بحق-الملكية.doc",
        "عقد-بيع-منقولات-وحدة-سكنية.doc",
        "عقد-رسمي-ببيع-سفينة.doc",
        "عقد-رسمي-ببيع-طائرة.doc",
    ],
    "عقود الإيجار": [
        "عقد إيجار محل تجاري.docx",
        "عقد إيجار.docx",
        "عقد إيجار سطح لوضع لافتة إعلانية.docx",
        "عقد ايجار.docx",
        "صيغة-عقد-إيجار-منقول.doc",
        "صيغة-عقد-ايجار-جدك.doc",
        "صيغة-عقد-ايجار-واجهة-أرض-فضاء-للاعلان.doc",
    ],
    "عقود المقاولة": [
        "عقد مقاولة 2.docx",
        "عقد مقاولة مع مهندس لعمل تصميم ومقايسة.docx",
        "عقد مقاولة من الباطن.docx",
        "عقد_مقاولة.docx",
    ],
    "عقود الوكالة والتوكيل": [
        "عقد اتفاق مع وكيل بالعمولة.docx",
        "صيغة-عقد-وكالة-بالعمولة.doc",
        "صيغة-عقد-توكيل-خاص-بشراء-عقار.doc",
        "صيغة-الغاء-توكيل.doc",
    ],
    "عقود الهبة": [
        "عقد هبة.docx",
        "عقد-رسمي-بهبة-عقار-بدون-عوض.doc",
        "عقد-رسمي-بهبة-عقار-بعوض.doc",
        "عقد-عرفي-بهبة-منقول.doc",
    ],
    "عقود القسمة والفرز": [
        "عقد قسمة مع فرز وتجنيب.docx",
        "عقد قسمة وفرز وتجنيب أرض زراعية.docx",
        "عقد_بيع_ابتدائي لحصة على المشاع.docx",
    ],
    "عقود الانتفاع وحقوق الارتفاق": [
        "عقد انتفاع بأرض فضاء لشخص معنوي.docx",
        "عقد انتفاع بمنقول.docx",
        "عقد رسمي لبيع حق انتفاع.docx",
        "عقد بيع حق رقبة مع الاحتفاظ بحق الانتفاع.docx",
        "عقد-بيع-حق-الانتفاع-2.doc",
        "صيغة-عقد-بتقرير-حق-ارتفاق.doc",
        "صيغة-عقد-بتقرير-حق-استعمال-لطريق-خاص.doc",
        "صيغة-عقد-بتقرير-حق-سكنى.doc",
        "عقد بتقرير حق سكنى.docx",
    ],
    "عقود الحراسة والوصاية": [
        "عقد بتعيين حارس على مال شائع.docx",
        "عقد تعيين حارس على تركة لخلاف على الاستحقاق فيها.docx",
        "صيغة-عقد-بتعيين-حارس-على-تركة.doc",
        "صيغة-عقد-بتعيين-حارس-على-مال-شائع.doc",
        "صيغة-وصية-شاملة-الحق-فى-العين-المؤجرة.doc",
    ],
    "عقود الرهن والضمان": [
        "عقد بترتيب دخل دائم مضمون برهن رسمي.docx",
        "صيغةعقد-رهن-رسمى-عقارى-ضمانا-لقرض-مع-تنازل-عن-مرتبة-رهن.doc",
    ],
    "عقود متخصصة": [
        "عقد فرانشيز.docx",
        "عقد طبع ونشر.docx",
        "عقد حفظ سرية و عدم إفصاح ثنائي اللغة.docx",
        "عقد اتعاب محاماه.docx",
        "عقد اتفاق مع موديل للدعاية.docx",
        "صيغة-عقد-العمل-البحرى.doc",
        "صيغة-تفاسخ-عن-عقد.doc",
        "بيع-بضاعة-بتظهير-سند-شحنها-أو-إيداعها.doc",
    ],
}

PARTY_ROLES: list[str] = [
    "بائع", "مشتري", "مؤجر", "مستأجر", "مقاول", "صاحب العمل",
    "موكل", "وكيل", "واهب", "موهوب له", "مرتهن", "راهن",
    "ناشر", "مؤلف", "محامي", "موكل المحامي", "أخرى",
]


def get_api_key(name: str) -> str:
    """Read a key from Streamlit session_state, secrets, then environment.

    Returns empty string if not found - callers decide whether to error.
    """
    try:
        import streamlit as st  # local import keeps this module importable without streamlit
        if hasattr(st, "session_state") and "user_api_keys" in st.session_state:
            val = st.session_state["user_api_keys"].get(name, "")
            if val:
                return str(val).strip()
        val = st.secrets.get(name, "")
        if val and val != "PASTE_YOUR_FRESH_GROQ_KEY_HERE":
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get(name, "").strip()
