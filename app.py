"""Egyptian Arabic Contract Generator - Streamlit front-end.

Pipeline (see ``agents.py``):

    Form / voice input
            v
    Drafter (Qwen3-32B on Groq, streamed JSON)
            v
    Critic (Llama-3.3-70B on Groq, strict review)
            v
    Chat refinement (per-clause edits)
            v
    Export: DOCX (RTL, Arabic font) + PDF + plain text
"""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

import agents
import config
import export
import rag
import templates
from schema import CritiqueReport, DraftedContract


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="مولد العقود المصرية",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# RTL stylesheet for the whole app
st.markdown(
    """
    <style>
      .stApp { direction: rtl; text-align: right; }
      .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
          direction: rtl; text-align: right;
      }
      div[data-testid="stChatMessage"] { direction: rtl; text-align: right; }
      .red-flag-critical { border-right: 4px solid #dc2626; padding: 0.5rem 1rem; margin: 0.5rem 0;
                          background: #fef2f2; border-radius: 4px; }
      .red-flag-high     { border-right: 4px solid #ea580c; padding: 0.5rem 1rem; margin: 0.5rem 0;
                          background: #fff7ed; border-radius: 4px; }
      .red-flag-medium   { border-right: 4px solid #ca8a04; padding: 0.5rem 1rem; margin: 0.5rem 0;
                          background: #fefce8; border-radius: 4px; }
      .red-flag-low      { border-right: 4px solid #16a34a; padding: 0.5rem 1rem; margin: 0.5rem 0;
                          background: #f0fdf4; border-radius: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="جاري تحميل نماذج العقود المصرية...")
def load_templates_cached() -> list[templates.LoadedTemplate]:
    return templates.load_all_templates(config.TEMPLATES_DIR, config.CONTRACT_CATEGORIES)


@st.cache_resource(show_spinner="جاري تحميل محرك البحث الدلالي (أول مرة فقط)...")
def warm_rag(_templates: list[templates.LoadedTemplate]) -> rag.ContractRAG:
    return rag.get_rag(_templates)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("contract", None)              # DraftedContract | None
    ss.setdefault("critique", None)              # CritiqueReport | None
    ss.setdefault("chat_history", [])            # list[dict[role, content]]
    ss.setdefault("voice_terms", "")             # transcribed special terms
    ss.setdefault("draft_raw", "")               # last raw JSON from drafter


_init_state()


# ---------------------------------------------------------------------------
# Sidebar - API + diagnostics
# ---------------------------------------------------------------------------
def _sidebar() -> None:
    with st.sidebar:
        st.header("⚖️ مولد العقود المصرية")
        st.caption("Egyptian Contract Drafting Assistant")
        st.divider()

        api_ok = bool(config.get_api_key("GROQ_API_KEY"))
        if api_ok:
            st.success("✅ مفتاح Groq مهيأ")
        else:
            st.error("❌ مفتاح Groq غير مهيأ")
            st.caption(
                "أضف `GROQ_API_KEY` في `.streamlit/secrets.toml`."
            )

        st.divider()
        st.subheader("النماذج المستخدمة")
        st.caption(f"الصياغة: `{config.DRAFTER_MODEL}`")
        st.caption(f"المراجعة: `{config.CRITIC_MODEL}`")
        st.caption(f"التفريغ الصوتي: `{config.WHISPER_MODEL}`")

        st.divider()
        if st.button("🗑️ مسح الجلسة", use_container_width=True):
            for k in ["contract", "critique", "chat_history", "voice_terms", "draft_raw"]:
                st.session_state[k] = None if k in ("contract", "critique") else (
                    "" if k in ("voice_terms", "draft_raw") else []
                )
            st.rerun()


_sidebar()


# ---------------------------------------------------------------------------
# Load templates + warm RAG (happens once per process)
# ---------------------------------------------------------------------------
all_templates = load_templates_cached()
if not all_templates:
    st.warning("لم يتم العثور على أي نماذج عقود. تأكد من وجود مجلد القوالب.")
    st.stop()
warm_rag(all_templates)


# ---------------------------------------------------------------------------
# Tabs: intake / draft / review / chat / export
# ---------------------------------------------------------------------------
tab_intake, tab_draft, tab_review, tab_chat, tab_export = st.tabs(
    ["١. البيانات", "٢. الصياغة", "٣. المراجعة", "٤. التعديل بالمحادثة", "٥. التصدير"]
)


# =============================================================================
# TAB 1 - INTAKE
# =============================================================================
with tab_intake:
    st.subheader("بيانات العقد")
    st.caption(
        "املأ النموذج أدناه. يمكنك تسجيل الشروط الخاصة صوتياً بدلاً من كتابتها."
    )

    col_l, col_r = st.columns(2)

    with col_l:
        category = st.selectbox("نوع العقد", list(config.CONTRACT_CATEGORIES.keys()))
        subject = st.text_area(
            "محل العقد (وصف موجز)",
            placeholder="مثال: بيع شقة سكنية رقم ٣ بالعقار الكائن في ...",
            height=100,
        )

        st.markdown("**الطرف الأول**")
        p1_name = st.text_input("الاسم", key="p1_name")
        p1_role = st.selectbox("الصفة", config.PARTY_ROLES, key="p1_role")
        p1_addr = st.text_area("العنوان", key="p1_addr", height=70)

        st.markdown("**الطرف الثاني**")
        p2_name = st.text_input("الاسم", key="p2_name")
        p2_role = st.selectbox("الصفة", config.PARTY_ROLES, key="p2_role", index=1)
        p2_addr = st.text_area("العنوان", key="p2_addr", height=70)

    with col_r:
        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("تاريخ بدء التنفيذ", value=date.today())
        with c2:
            end_d = st.date_input("تاريخ الانتهاء", value=date.today())

        contract_value = st.text_input("قيمة العقد", placeholder="مثال: ١,٥٠٠,٠٠٠ جنيه مصري")
        payment_terms = st.text_area(
            "شروط الدفع",
            placeholder="مثال: ٣٠٪ عند التوقيع، ٤٠٪ عند التسليم، ٣٠٪ بعد التشغيل التجريبي",
            height=80,
        )
        jurisdiction = st.text_input(
            "القانون الحاكم / المحكمة المختصة",
            value="القانون المصري - محاكم القاهرة الاقتصادية",
        )

        st.markdown("**شروط خاصة**")
        st.caption("اكتبها أو سجّلها صوتياً (Whisper Large v3 على Groq).")
        audio = st.audio_input("🎤 تسجيل صوتي بالعربية", key="voice_input")
        if audio is not None and st.button("تفريغ التسجيل", use_container_width=True):
            with st.spinner("جاري التفريغ..."):
                try:
                    transcript = agents.transcribe_special_terms(audio.getvalue())
                    st.session_state["voice_terms"] = transcript
                    st.success("تم التفريغ.")
                except Exception as e:
                    st.error(f"تعذّر التفريغ: {e}")

        special_terms = st.text_area(
            "نص الشروط الخاصة",
            value=st.session_state["voice_terms"],
            height=140,
            key="special_terms_field",
        )

        client_party = st.selectbox(
            "مَن هو موكّلك؟ (يستخدمها المراجع للتركيز على مصلحته)",
            ["الطرف الأول", "الطرف الثاني"],
        )

    st.divider()
    if st.button("➡️ الانتقال إلى الصياغة", type="primary", use_container_width=True):
        st.session_state["request"] = agents.ContractRequest(
            category=category,
            subject=subject,
            party1_name=p1_name,
            party1_role=p1_role,
            party1_address=p1_addr,
            party2_name=p2_name,
            party2_role=p2_role,
            party2_address=p2_addr,
            start_date=str(start_d),
            end_date=str(end_d),
            contract_value=contract_value,
            payment_terms=payment_terms,
            jurisdiction=jurisdiction,
            special_terms=special_terms,
            client_party=client_party,
        )
        st.success("✅ البيانات مهيأة. انتقل إلى تبويب «الصياغة» واضغط على «إنشاء العقد».")


# =============================================================================
# TAB 2 - DRAFT
# =============================================================================
with tab_draft:
    st.subheader("صياغة العقد")
    req = st.session_state.get("request")
    if req is None:
        st.info("املأ البيانات في التبويب الأول أولاً.")
    else:
        st.caption(
            f"النوع: **{req.category}** | {req.party1_name or '...'} ({req.party1_role}) "
            f"و {req.party2_name or '...'} ({req.party2_role})"
        )
        if st.button("✍️ إنشاء العقد", type="primary", use_container_width=True):
            placeholder = st.empty()
            raw_acc = ""
            try:
                for accumulated, _delta in agents.stream_draft(req, all_templates):
                    raw_acc = accumulated
                    placeholder.code(
                        accumulated[-1500:],  # show only the tail to keep UI fast
                        language="json",
                    )
                # parse
                contract = agents.parse_draft(raw_acc)
                st.session_state["contract"] = contract
                st.session_state["draft_raw"] = raw_acc
                st.session_state["critique"] = None  # invalidate previous critique
                placeholder.empty()
                st.success("✅ تم إنشاء العقد. انتقل إلى تبويب «المراجعة» أو «التصدير».")
            except json.JSONDecodeError as e:
                st.error(f"خرج النموذج بنص JSON غير صالح: {e}")
                with st.expander("النص الخام"):
                    st.code(raw_acc)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الصياغة: {e}")

        contract: DraftedContract | None = st.session_state.get("contract")
        if contract is not None:
            st.divider()
            st.markdown("### معاينة العقد")
            st.markdown(f"**{contract.title}**")
            if contract.preamble:
                st.write(contract.preamble)
            st.markdown("**الأطراف:**")
            for i, p in enumerate(contract.parties, start=1):
                st.write(f"- الطرف {i}: {p.name} ({p.role})")
            for art in contract.articles:
                with st.expander(f"البند {art.number}: {art.title}", expanded=False):
                    st.write(art.body)
            st.markdown(f"**القانون الحاكم:** {contract.governing_law}")


# =============================================================================
# TAB 3 - REVIEW
# =============================================================================
def _render_red_flag(rf, idx: int) -> None:
    severity_class = f"red-flag-{rf.severity}"
    title = f"#{idx}. "
    if rf.article_number is not None:
        title += f"البند {rf.article_number} — "
    title += f"**{rf.category}** (خطورة: {rf.severity})"
    st.markdown(
        f"<div class='{severity_class}'>"
        f"<div>{title}</div>"
        f"<div><b>المشكلة:</b> {rf.issue}</div>"
        f"<div><b>الحل المقترح:</b> {rf.suggested_fix}</div>"
        f"{('<div><b>المرجع:</b> ' + rf.civil_code_reference + '</div>') if rf.civil_code_reference else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )


with tab_review:
    st.subheader("المراجعة الصارمة")
    contract: DraftedContract | None = st.session_state.get("contract")
    if contract is None:
        st.info("أنشئ عقداً أولاً في تبويب «الصياغة».")
    else:
        req = st.session_state.get("request")
        client_party = req.client_party if req else "الطرف الأول"
        if st.button("🔍 تشغيل المراجع", type="primary", use_container_width=True):
            with st.spinner("جاري المراجعة..."):
                try:
                    report = agents.run_critic(contract, client_party=client_party)
                    st.session_state["critique"] = report
                except Exception as e:
                    st.error(f"تعذّرت المراجعة: {e}")

        critique: CritiqueReport | None = st.session_state.get("critique")
        if critique is not None:
            st.markdown(f"**تقييم عام:** `{critique.overall_quality}`")
            st.info(critique.summary)
            if not critique.red_flags:
                st.success("لا توجد ملاحظات جوهرية.")
            else:
                # sort by severity
                order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                sorted_flags = sorted(
                    critique.red_flags, key=lambda r: order.get(r.severity, 99)
                )
                for i, rf in enumerate(sorted_flags, start=1):
                    _render_red_flag(rf, i)


# =============================================================================
# TAB 4 - CHAT REFINEMENT
# =============================================================================
with tab_chat:
    st.subheader("تعديل العقد بالمحادثة")
    contract: DraftedContract | None = st.session_state.get("contract")
    if contract is None:
        st.info("أنشئ عقداً أولاً في تبويب «الصياغة».")
    else:
        st.caption(
            "اطلب أي تعديل بالعربية. مثال: «اجعل الشرط الجزائي في البند الرابع ضعف القيمة»"
            " أو «أضف بند تحكيم بمركز القاهرة الإقليمي»."
        )
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_msg = st.chat_input("اكتب طلب التعديل...")
        if user_msg:
            st.session_state["chat_history"].append({"role": "user", "content": user_msg})
            with st.chat_message("user"):
                st.write(user_msg)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.write("جاري التعديل...")
                raw_acc = ""
                try:
                    for accumulated, _delta in agents.stream_refine(contract, user_msg):
                        raw_acc = accumulated
                    new_contract = agents.parse_draft(raw_acc)
                    st.session_state["contract"] = new_contract
                    st.session_state["critique"] = None  # invalidate
                    placeholder.success("✅ تم تطبيق التعديل. راجع التبويبات لرؤية النتيجة.")
                    st.session_state["chat_history"].append(
                        {"role": "assistant", "content": "تم تطبيق التعديل بنجاح."}
                    )
                except Exception as e:
                    placeholder.error(f"تعذّر التعديل: {e}")
                    st.session_state["chat_history"].append(
                        {"role": "assistant", "content": f"تعذّر التعديل: {e}"}
                    )


# =============================================================================
# TAB 5 - EXPORT
# =============================================================================
with tab_export:
    st.subheader("تصدير العقد")
    contract: DraftedContract | None = st.session_state.get("contract")
    if contract is None:
        st.info("أنشئ عقداً أولاً.")
    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            try:
                docx_bytes = export.contract_to_docx(contract)
                st.download_button(
                    "⬇️ تحميل DOCX",
                    data=docx_bytes,
                    file_name="contract.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"تعذّر إنشاء DOCX: {e}")

        with c2:
            try:
                pdf_bytes = export.contract_to_pdf(contract)
                st.download_button(
                    "⬇️ تحميل PDF",
                    data=pdf_bytes,
                    file_name="contract.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"تعذّر إنشاء PDF: {e}")

        with c3:
            txt = export.contract_to_text(contract)
            st.download_button(
                "⬇️ تحميل نص",
                data=txt.encode("utf-8"),
                file_name="contract.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.divider()
        st.markdown("### نسخة JSON (للنسخ الاحتياطي)")
        st.code(contract.model_dump_json(indent=2), language="json")

        st.caption(
            "⚠️ المحتوى المولّد بواسطة الذكاء الاصطناعي مرجعي فقط، ولا يغني عن مراجعة محامٍ مختص."
        )
