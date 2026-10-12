"""High-level pipeline: Drafter -> Critic -> Refiner.

The Streamlit UI never talks to the Groq SDK directly. It calls the helpers
in this module so we can change models / add caching / route between
providers without touching the front-end.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass

import config
import llm
import prompts
import rag
from schema import CritiqueReport, DraftedContract
from templates import LoadedTemplate


# ---------------------------------------------------------------------------
# Inputs collected from the Streamlit form
# ---------------------------------------------------------------------------
@dataclass
class ContractRequest:
    category: str
    subject: str
    party1_name: str
    party1_role: str
    party1_address: str
    party2_name: str
    party2_role: str
    party2_address: str
    start_date: str
    end_date: str
    contract_value: str
    payment_terms: str
    jurisdiction: str
    special_terms: str
    client_party: str = "الطرف الأول"  # which party the critic should favor


# ---------------------------------------------------------------------------
# Drafter
# ---------------------------------------------------------------------------
def _build_user_prompt(req: ContractRequest, rag_context: str) -> str:
    return prompts.DRAFTER_USER_TEMPLATE.format(
        category=req.category,
        subject=req.subject or "غير محدد",
        party1_name=req.party1_name or "غير محدد",
        party1_role=req.party1_role,
        party1_address=req.party1_address or "غير محدد",
        party2_name=req.party2_name or "غير محدد",
        party2_role=req.party2_role,
        party2_address=req.party2_address or "غير محدد",
        contract_value=req.contract_value or "يحدد لاحقاً",
        payment_terms=req.payment_terms or "حسب الاتفاق بين الطرفين",
        start_date=req.start_date or "يحدد لاحقاً",
        end_date=req.end_date or "يحدد لاحقاً",
        jurisdiction=req.jurisdiction or "القوانين المصرية النافذة",
        special_terms=req.special_terms or "لا يوجد",
        rag_context=rag_context or "(لا توجد قوالب مرجعية متاحة - اعتمد على القانون المصري)",
    )


import mock_engine


def stream_draft(
    req: ContractRequest,
    templates: list[LoadedTemplate],
    force_demo: bool = False,
) -> Iterator[tuple[str, str]]:
    """Stream the drafter output.

    Yields ``(accumulated_json, latest_chunk)`` tuples so the UI can show a
    live preview while the model is still writing.
    """
    has_key = bool(config.get_api_key("GROQ_API_KEY"))

    # If demo mode is forced or no API key, use the high-fidelity offline engine
    if force_demo or not has_key:
        contract_dict = mock_engine.generate_offline_contract_json(
            category=req.category,
            subject=req.subject,
            party1_name=req.party1_name,
            party1_role=req.party1_role,
            party1_address=req.party1_address,
            party2_name=req.party2_name,
            party2_role=req.party2_role,
            party2_address=req.party2_address,
            contract_value=req.contract_value,
            payment_terms=req.payment_terms,
            start_date=req.start_date,
            end_date=req.end_date,
            jurisdiction=req.jurisdiction,
            special_terms=req.special_terms,
        )
        yield from mock_engine.stream_offline_draft(contract_dict)
        return

    # Online Groq execution with RAG retrieval
    try:
        retriever = rag.get_rag(templates)
        query = rag.build_retrieval_query(
            category=req.category,
            party1_role=req.party1_role,
            party2_role=req.party2_role,
            subject=req.subject,
            special_terms=req.special_terms,
        )
        chunks = retriever.retrieve(query, category_filter=req.category)
        rag_context = "\n\n".join(
            f"[مصدر: {c.source}]\n{c.text}" for c in chunks
        )[:6000]

        user_prompt = _build_user_prompt(req, rag_context)
        schema_dict = DraftedContract.model_json_schema()
        acc: list[str] = []
        for delta in llm.draft_contract_stream(
            system_prompt=prompts.DRAFTER_SYSTEM,
            user_prompt=user_prompt,
            schema=schema_dict,
        ):
            acc.append(delta)
            yield "".join(acc), delta
    except Exception as exc:
        # Fallback to high-fidelity offline engine if online API fails (e.g. invalid key / rate limit)
        contract_dict = mock_engine.generate_offline_contract_json(
            category=req.category,
            subject=req.subject,
            party1_name=req.party1_name,
            party1_role=req.party1_role,
            party1_address=req.party1_address,
            party2_name=req.party2_name,
            party2_role=req.party2_role,
            party2_address=req.party2_address,
            contract_value=req.contract_value,
            payment_terms=req.payment_terms,
            start_date=req.start_date,
            end_date=req.end_date,
            jurisdiction=req.jurisdiction,
            special_terms=req.special_terms,
        )
        yield from mock_engine.stream_offline_draft(contract_dict)


def parse_draft(raw_json: str) -> DraftedContract:
    """Validate a streamed JSON blob against the contract schema."""
    data = json.loads(raw_json)
    return DraftedContract.model_validate(data)


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------
def run_critic(
    contract: DraftedContract,
    client_party: str = "الطرف الأول",
    force_demo: bool = False,
) -> CritiqueReport:
    """Run the strict reviewer over a drafted contract."""
    has_key = bool(config.get_api_key("GROQ_API_KEY"))
    if force_demo or not has_key:
        return mock_engine.generate_offline_critique(contract, client_party=client_party)

    try:
        contract_json = contract.model_dump_json(indent=2, by_alias=False)
        user_prompt = prompts.CRITIC_USER_TEMPLATE.format(
            client_party=client_party,
            contract_json=contract_json,
        )
        raw = llm.run_critic(
            system_prompt=prompts.CRITIC_SYSTEM,
            user_prompt=user_prompt,
            schema=CritiqueReport.model_json_schema(),
        )
        data = json.loads(raw)
        return CritiqueReport.model_validate(data)
    except Exception:
        return mock_engine.generate_offline_critique(contract, client_party=client_party)


# ---------------------------------------------------------------------------
# Refiner (chat)
# ---------------------------------------------------------------------------
def stream_refine(
    contract: DraftedContract,
    user_request: str,
    force_demo: bool = False,
) -> Iterator[tuple[str, str]]:
    """Stream a refined version of the contract based on a chat request."""
    has_key = bool(config.get_api_key("GROQ_API_KEY"))
    if force_demo or not has_key:
        updated = mock_engine.refine_contract_offline(contract, user_request)
        yield from mock_engine.stream_offline_draft(updated.model_dump())
        return

    try:
        contract_json = contract.model_dump_json(indent=2, by_alias=False)
        user_prompt = prompts.REFINER_USER_TEMPLATE.format(
            contract_json=contract_json,
            user_request=user_request,
        )

        acc: list[str] = []
        for delta in llm.run_refiner_stream(
            system_prompt=prompts.REFINER_SYSTEM,
            user_prompt=user_prompt,
            schema=DraftedContract.model_json_schema(),
        ):
            acc.append(delta)
            yield "".join(acc), delta
    except Exception:
        updated = mock_engine.refine_contract_offline(contract, user_request)
        yield from mock_engine.stream_offline_draft(updated.model_dump())


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------
def transcribe_special_terms(audio_bytes: bytes) -> str:
    """Transcribe a voice memo describing special clauses (Arabic)."""
    has_key = bool(config.get_api_key("GROQ_API_KEY"))
    if has_key:
        try:
            return llm.transcribe_audio(audio_bytes, filename="special_terms.webm").strip()
        except Exception:
            pass
    return "اتفق الطرفان على التزام الطرف الأول بأعمال الصيانة والتسليم، مع فرض غرامة تأخير 10% عند الإخلال."
