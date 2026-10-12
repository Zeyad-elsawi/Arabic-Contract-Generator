"""Egyptian Arabic Contract Generator - Professional Streamlit Interface.

Architecture:
    Form / Voice Input (Intake)
            v
    RAG Engine (BAAI/bge-m3 embeddings + FAISS vector store over 74 Egyptian legal templates)
            v
    Drafter Agent (Qwen/Llama on Groq OR High-Fidelity Egyptian Legal Engine in Demo Mode)
            v
    Critic Agent (Strict Egyptian Civil Code legal review & Red Flags)
            v
    Chat Refinement (Per-clause natural language modifications)
            v
    Multi-Format Export: DOCX (RTL, Table styling) + PDF (Arabic Reshaper + Bidi) + Plain Text
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
# Page configuration & Modern Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="نظام صياغة ومراجعة العقود المصرية الذكي",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
      
      html, body, [class*="css"], .stApp {
          font-family: 'Cairo', -apple-system, BlinkMacSystemFont, sans-serif !important;
          direction: rtl;
          text-align: right;
      }
      
      /* Global text alignment for Arabic RTL */
      .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
          direction: rtl;
          text-align: right;
          font-family: 'Cairo', sans-serif !important;
      }
      div[data-testid="stChatMessage"] {
          direction: rtl;
          text-align: right;
          font-family: 'Cairo', sans-serif !important;
      }

      /* Hero Header Banner */
      .main-header {
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f766e 100%);
          color: white;
          padding: 1.5rem 2rem;
          border-radius: 12px;
          margin-bottom: 1.5rem;
          box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      }
      .main-header h1 {
          color: #f8fafc;
          font-size: 1.85rem;
          font-weight: 800;
          margin: 0 0 0.4rem 0;
      }
      .main-header p {
          color: #94a3b8;
          font-size: 0.95rem;
          margin: 0;
      }
      .badge-chip {
          display: inline-block;
          background: rgba(255, 255, 255, 0.15);
          color: #f1f5f9;
          font-size: 0.75rem;
          padding: 0.2rem 0.6rem;
          border-radius: 9999px;
          margin-left: 0.5rem;
      }

      /* Red Flag Styling Cards */
      .red-flag-card {
          padding: 1rem 1.25rem;
          margin: 0.75rem 0;
          border-radius: 8px;
          font-size: 0.95rem;
          line-height: 1.6;
      }
      .red-flag-critical {
          border-right: 5px solid #dc2626;
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
      }
      .red-flag-high {
          border-right: 5px solid #ea580c;
          background: #fff7ed;
          border: 1px solid #fed7aa;
          color: #9a3412;
      }
      .red-flag-medium {
          border-right: 5px solid #d97706;
          background: #fffbeb;
          border: 1px solid #fde68a;
          color: #92400e;
      }
      .red-flag-low {
          border-right: 5px solid #059669;
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          color: #166534;
      }

      /* Article Box Styling */
      .article-box {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 0.75rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Cached Resources
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="جاري تحميل قوالب العقود ونماذج الصياغة...")
def load_templates_cached() -> list[templates.LoadedTemplate]:
    return templates.load_all_templates(config.TEMPLATES_DIR, config.CONTRACT_CATEGORIES)


@st.cache_resource(show_spinner="جاري تحميل الفهرس الدلالي RAG (FAISS)...")
def warm_rag(_templates: list[templates.LoadedTemplate]) -> rag.ContractRAG:
    return rag.get_rag(_templates)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("contract", None)              # DraftedContract | None
    ss.setdefault("critique", None)              # CritiqueReport | None
    ss.setdefault("chat_history", [])            # list[dict[role, content]]
    ss.setdefault("voice_terms", "")             # transcribed special terms
    ss.setdefault("draft_raw", "")               # last raw JSON from drafter
    ss.setdefault("demo_mode", True)             # Default to Demo/Offline resilient mode
    ss.setdefault("user_api_keys", {})           # Runtime override keys
    ss.setdefault("form_category", "عقود البيع")
    ss.setdefault("form_subject", "")
    ss.setdefault("form_p1_name", "")
    ss.setdefault("form_p1_role", "بائع")
    ss.setdefault("form_p1_addr", "")
    ss.setdefault("form_p2_name", "")
    ss.setdefault("form_p2_role", "مشتري")
    ss.setdefault("form_p2_addr", "")
    ss.setdefault("form_val", "")
    ss.setdefault("form_pay", "")
    ss.setdefault("form_juris", "القانون المدني المصري - محاكم القاهرة الابتدائية")
    ss.setdefault("form_client", "الطرف الثاني")


_init_state()


# ---------------------------------------------------------------------------
# Load templates + warm RAG
# ---------------------------------------------------------------------------
all_templates = load_templates_cached()
warm_rag(all_templates)


# ---------------------------------------------------------------------------
# Sidebar - Settings, API, Presets & Diagnostics
# ---------------------------------------------------------------------------
def _sidebar() -> None:
    with st.sidebar:
        st.markdown("### ⚖️ لوحة التحكم والإعدادات")
        st.caption("نظام وكلاء الذكاء الاصطناعي للمحامين والمستشارين")
        st.divider()

        # Engine Mode Selector
        groq_key = config.get_api_key("GROQ_API_KEY")
        has_key = bool(groq_key)

        st.markdown("**وضع المعالجة والذكاء الاصطناعي:**")
        selected_mode = st.radio(
            "اختر وضع التشغيل",
            options=["محاكاة ذكية متكاملة (Offline Demo)", "سحابي مباشر (Groq Cloud LLM)"],
            index=0 if not has_key else 1,
            label_visibility="collapsed",
        )
        st.session_state["demo_mode"] = (selected_mode == "محاكاة ذكية متكاملة (Offline Demo)")

        if not st.session_state["demo_mode"]:
            st.info("⚡ وضع Groq السحابي مفعل (استدعاء نماذج Llama-3.3-70B)")
            key_input = st.text_input(
                "مفتاح Groq API Key:",
                value=groq_key,
                type="password",
                help="احصل على مفتاح مجاني من console.groq.com",
            )
            if key_input != groq_key:
                st.session_state["user_api_keys"]["GROQ_API_KEY"] = key_input.strip()
                st.rerun()
        else:
            st.success("🛡️ المحاكاة الذكية مفعلة (جاهز للعرض والتشغيل الفوري دون الحاجة لمفتاح)")

        st.divider()

        # Quick Preset loader for instant demo
        st.markdown("**⚡ سيناريو تجريبي فوري:**")
        if st.button("ملء نموذج بيع شقة (التجمع الخامس)", use_container_width=True):
            st.session_state["form_category"] = "عقود البيع"
            st.session_state["form_subject"] = "بيع شقة سكنية رقم ٤ بالدور الثاني بالعقار الكائن بالحي الخامس، التجمع الخامس، القاهرة الجديدة بمساحة ١٨٠ م٢."
            st.session_state["form_p1_name"] = "م. حسام الدين كمال المنشاوي"
            st.session_state["form_p1_role"] = "بائع"
            st.session_state["form_p1_addr"] = "٤٥ شارع الثورة، مصر الجديدة، القاهرة"
            st.session_state["form_p2_name"] = "أ. طارق محمود عبد العزيز"
            st.session_state["form_p2_role"] = "مشتري"
            st.session_state["form_p2_addr"] = "١٢ شارع دجلة، المعادي، القاهرة"
            st.session_state["form_val"] = "٣,٥٠٠,٠٠٠ جنيه مصري (ثلاثة ملايين وخمسمائة ألف جنيه)"
            st.session_state["form_pay"] = "سداد ٥٠٪ دفعة مقدمة عند التوقيع، و٢٥٪ عند الاستلام الفعلي، و٢٥٪ على أقساط ربع سنوية."
            st.session_state["voice_terms"] = "يلتزم البائع بتسليم الشقة مشطبة سوبر لوكس شاملاً حصة في الجراج والأرض، مع غرامة تأخير ١٠٪، والتزام بالحضور أمام الشهر العقاري لنقل الملكية."
            st.session_state["form_client"] = "الطرف الثاني"
            st.success("تم ملء البيانات بنجاح! انتقل للصياغة.")
            st.rerun()

        st.divider()
        st.markdown("**إحصائيات النظام:**")
        st.caption(f"📁 القوالب المفهرسة: **{len(all_templates)} نموذج مصري أصيل**")
        st.caption(f"🧠 محرك التضمين: **{config.EMBEDDING_MODEL}**")
        st.caption(f"🤖 نموذج الصياغة: **{config.DRAFTER_MODEL}**")
        st.caption(f"🧐 نموذج المراجعة: **{config.CRITIC_MODEL}**")

        st.divider()
        if st.button("🗑️ إعادة تعيين الجلسة", use_container_width=True):
            for k in ["contract", "critique", "chat_history", "voice_terms", "draft_raw", "request"]:
                if k in st.session_state:
                    del st.session_state[k]
            _init_state()
            st.rerun()


_sidebar()


# ---------------------------------------------------------------------------
# Main Executive Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
      <h1>⚖️ المنظومة الذكية لصياغة ومراجعة العقود المصرية</h1>
      <p>
        نظام ذكاء اصطناعي متعدد الوكلاء (Multi-Agent System) مدعوم بتقنية البحث الدلالي المتقدم (RAG) 
        وفقاً لأحكام القانون المدني وقانون التجارة المصريين.
        <br>
        <span class="badge-chip">Drafter Agent</span>
        <span class="badge-chip">Senior Critic Agent</span>
        <span class="badge-chip">Conversational Refiner</span>
        <span class="badge-chip">RTL DOCX & PDF Export</span>
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Tabs Navigation
# ---------------------------------------------------------------------------
tab_intake, tab_draft, tab_review, tab_chat, tab_export = st.tabs(
    ["١. إدخال البيانات", "٢. الصياغة الآلية", "٣. المراجعة القانونية الصارمة", "٤. التعديل بالمحادثة", "٥. التصدير والطباعة"]
)


# =============================================================================
# TAB 1 - INTAKE
# =============================================================================
with tab_intake:
    st.markdown("### بيانات ومحددات العقد")
    st.caption("أدخل بيانات العقد، أو اضغط على «ملء نموذج بيع شقة» في الشريط الجانبي لتجربة فورية سريعة.")

    col_l, col_r = st.columns(2)

    with col_l:
        cat_index = 0
        cats = list(config.CONTRACT_CATEGORIES.keys())
        if st.session_state["form_category"] in cats:
            cat_index = cats.index(st.session_state["form_category"])
        category = st.selectbox("نوع وتصنيف العقد", cats, index=cat_index)
        
        subject = st.text_area(
            "محل العقد وموضوعه بالتفصيل",
            value=st.session_state["form_subject"],
            placeholder="مثال: بيع شقة سكنية رقم ٤ بالعقار الكائن في...",
            height=110,
        )

        st.markdown("#### الطرف الأول")
        p1_name = st.text_input("اسم الطرف الأول", value=st.session_state["form_p1_name"])
        p1_roles = config.PARTY_ROLES
        p1_role = st.selectbox("صفته في العقد", p1_roles, index=p1_roles.index(st.session_state["form_p1_role"]) if st.session_state["form_p1_role"] in p1_roles else 0)
        p1_addr = st.text_input("محل الإقامة / المقر القانوني", value=st.session_state["form_p1_addr"])

        st.markdown("#### الطرف الثاني")
        p2_name = st.text_input("اسم الطرف الثاني", value=st.session_state["form_p2_name"])
        p2_role = st.selectbox("صفته في العقد", p1_roles, index=p1_roles.index(st.session_state["form_p2_role"]) if st.session_state["form_p2_role"] in p1_roles else 1)
        p2_addr = st.text_input("محل الإقامة / المقر القانوني (طرف ثان)", value=st.session_state["form_p2_addr"])

    with col_r:
        st.markdown("#### البيانات المالية والزمنية")
        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("تاريخ بدء السريان والتنفيذ", value=date.today())
        with c2:
            end_d = st.date_input("تاريخ انتهاء السريان / التسليم", value=date.today())

        contract_value = st.text_input(
            "قيمة العقد والمقابل المالي",
            value=st.session_state["form_val"],
            placeholder="مثال: ٣,٥٠٠,٠٠٠ جنيه مصري",
        )
        payment_terms = st.text_area(
            "شروط وطريقة الدفع",
            value=st.session_state["form_pay"],
            placeholder="مثال: ٥٠٪ مقدم عند التوقيع والباقي على دفعات...",
            height=80,
        )
        jurisdiction = st.text_input(
            "القانون الحاكم والمحكمة المختصة",
            value=st.session_state["form_juris"],
        )

        st.markdown("#### الشروط الخاصة والإدخال الصوتي")
        st.caption("اكتب الشروط الإضافية أو سجّلها صوتياً (Whisper v3).")
        audio = st.audio_input("تسجيل صوتي للشروط الخاصة", key="voice_mic")
        if audio is not None and st.button("🎙️ تفريغ التسجيل الصوتي", use_container_width=True):
            with st.spinner("جاري تفريغ الصوت وتحليله..."):
                transcript = agents.transcribe_special_terms(audio.getvalue())
                st.session_state["voice_terms"] = transcript
                st.success("تم تفريغ الملاحظات الصوتية بنجاح.")

        special_terms = st.text_area(
            "نص الشروط الخاصة والملاحظات الإضافية",
            value=st.session_state["voice_terms"],
            height=120,
        )

        client_party = st.selectbox(
            "الطرف الموكل (الذي يُركز عليه المراجع لحماية حقوقه)",
            ["الطرف الثاني", "الطرف الأول"],
            index=0 if st.session_state["form_client"] == "الطرف الثاني" else 1,
        )

    st.divider()
    if st.button("➡️ اعتماد البيانات والانتقال إلى الصياغة", type="primary", use_container_width=True):
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
        st.success("✅ تم حفظ البيانات بنجاح. انتقل الآن إلى تبويب «٢. الصياغة الآلية».")


# =============================================================================
# TAB 2 - DRAFT
# =============================================================================
with tab_draft:
    st.markdown("### صياغة العقد بواسطة الوكيل القانوني (Drafter Agent)")
    req = st.session_state.get("request")

    if req is None:
        st.warning("يرجى ملء البيانات أولاً في تبويب «١. إدخال البيانات» أو الضغط على الزر التجريبي في الشريط الجانبي.")
    else:
        st.info(
            f"📋 **نوع العقد:** {req.category} | **الطرف الأول:** {req.party1_name or '...'} ({req.party1_role}) "
            f"| **الطرف الثاني:** {req.party2_name or '...'} ({req.party2_role})"
        )

        is_demo = st.session_state.get("demo_mode", True)
        if st.button("✍️ إنشاء وصياغة العقد بالكامل", type="primary", use_container_width=True):
            placeholder = st.empty()
            raw_acc = ""
            status_text = st.empty()
            status_text.caption("جاري البحث في قاعدة النماذج المصرية وتوليد البنود بالذكاء الاصطناعي...")

            try:
                for accumulated, _delta in agents.stream_draft(req, all_templates, force_demo=is_demo):
                    raw_acc = accumulated
                    placeholder.code(accumulated[-1500:], language="json")

                contract = agents.parse_draft(raw_acc)
                st.session_state["contract"] = contract
                st.session_state["draft_raw"] = raw_acc
                st.session_state["critique"] = None
                placeholder.empty()
                status_text.empty()
                st.success("✅ تم الانتهاء من صياغة العقد بنجاح وحفظه.")
            except Exception as e:
                st.error(f"حدث خطأ أثناء الصياغة: {e}")

        contract: DraftedContract | None = st.session_state.get("contract")
        if contract is not None:
            st.divider()
            st.markdown(f"## {contract.title}")
            
            with st.container():
                st.markdown(f"**الديباجة:**\n\n{contract.preamble}")

            st.markdown("#### الأطراف المتعاقدة:")
            p_cols = st.columns(len(contract.parties))
            for i, (col, party) in enumerate(zip(p_cols, contract.parties), start=1):
                with col:
                    st.markdown(
                        f"""
                        <div class="article-box">
                          <b>الطرف {i} ({party.role})</b><br>
                          الاسم: {party.name}<br>
                          العنوان: {party.address or 'غير محدد'}<br>
                          الرقم القومي: {party.national_id or 'مسجل'}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if contract.recitals:
                with st.expander("📌 التمهيد والحيثيات (Recitals)", expanded=True):
                    for r in contract.recitals:
                        st.markdown(f"- {r}")

            st.markdown(f"#### بنود العقد ({len(contract.articles)} بنداً):")
            for art in contract.articles:
                with st.expander(f"البند {art.number}: {art.title}", expanded=True):
                    st.write(art.body)

            st.markdown(f"**القانون الحاكم:** {contract.governing_law}")
            st.caption(contract.signature_block)


# =============================================================================
# TAB 3 - REVIEW (CRITIC AGENT)
# =============================================================================
with tab_review:
    st.markdown("### المراجعة القانونية الصارمة (Senior Critic Agent)")
    contract: DraftedContract | None = st.session_state.get("contract")

    if contract is None:
        st.warning("يرجى صياغة العقد أولاً في تبويب «٢. الصياغة الآلية».")
    else:
        req = st.session_state.get("request")
        client_party = req.client_party if req else "الطرف الثاني"
        is_demo = st.session_state.get("demo_mode", True)

        st.caption(
            f"يقوم المراجع بفحص العقد نيابة عن **{client_party}** لاكتشاف الثغرات وشروط الإذعان "
            "ومطابقة البنود لأحكام القانون المدني المصري رقم 131 لسنة 1948."
        )

        if st.button("🔍 تشغيل الفحص القانوني الصارم", type="primary", use_container_width=True):
            with st.spinner("جاري تحليل بنود العقد واكتشاف المخاطر والملاحظات..."):
                try:
                    report = agents.run_critic(contract, client_party=client_party, force_demo=is_demo)
                    st.session_state["critique"] = report
                    st.success("تم إتمام الفحص القانوني الشامل.")
                except Exception as e:
                    st.error(f"تعذرت المراجعة: {e}")

        critique: CritiqueReport | None = st.session_state.get("critique")
        if critique is not None:
            st.divider()
            c_meta1, c_meta2 = st.columns([1, 3])
            with c_meta1:
                st.metric("التقييم العام للمخاطر", critique.overall_quality.upper())
            with c_meta2:
                st.info(critique.summary)

            st.markdown(f"#### الملاحظات القانونية المرصودة ({len(critique.red_flags)} ملاحظة):")
            for i, rf in enumerate(critique.red_flags, start=1):
                severity_class = f"red-flag-{rf.severity}"
                ref_text = f"<br><b>المرجع القانوني:</b> {rf.civil_code_reference}" if rf.civil_code_reference else ""
                art_header = f"البند {rf.article_number} — " if rf.article_number else ""
                
                st.markdown(
                    f"""
                    <div class="red-flag-card {severity_class}">
                      <b>#{i}. {art_header}{rf.category} (الخطورة: {rf.severity.upper()})</b><br>
                      <b>المشكلة المرصودة:</b> {rf.issue}<br>
                      <b>الحل والتعديل المقترح:</b> {rf.suggested_fix}
                      {ref_text}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# =============================================================================
# TAB 4 - CHAT REFINEMENT
# =============================================================================
with tab_chat:
    st.markdown("### التعديل التفاعلي بالمحادثة (Refiner Agent)")
    contract: DraftedContract | None = st.session_state.get("contract")

    if contract is None:
        st.warning("يرجى صياغة العقد أولاً في تبويب «٢. الصياغة الآلية».")
    else:
        st.caption("اطلب أي تعديل باللغة العربية، مثل إضافة شرط تحكيم، أو تعديل الشرط الجزائي، أو تحديد مسؤوليات إضافية.")

        # Quick action suggestions
        st.markdown("**أوامر تعديل سريعة شائعة:**")
        q1, q2, q3 = st.columns(3)
        quick_prompt = None
        if q1.button("⚖️ أضف شرط تحكيم (CRCICA)", use_container_width=True):
            quick_prompt = "أضف شرط فض النزاعات عن طريق التحكيم بمركز القاهرة الإقليمي للتحكيم التجاري الدولي CRCICA"
        if q2.button("💰 ارفع الشرط الجزائي إلى 25%", use_container_width=True):
            quick_prompt = "اجعل الشرط الجزائي في العقد بنسبة 25% من إجمالي القيمة أو 100,000 جنيه أيهما أكبر"
        if q3.button("⚡ صيغة شرط فاسخ صريح", use_container_width=True):
            quick_prompt = "اجعل صيغة الفسخ شرطاً فاسخاً صريحاً دون حاجة إلى تنبيه أو إنذار أو حكم قضائي طبقاً للمادة 158 مدني"

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_msg = st.chat_input("اكتب طلب التعديل هنا...") or quick_prompt
        if user_msg:
            st.session_state["chat_history"].append({"role": "user", "content": user_msg})
            with st.chat_message("user"):
                st.write(user_msg)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.write("جاري تعديل العقد وتحديث بنوده...")
                raw_acc = ""
                is_demo = st.session_state.get("demo_mode", True)
                try:
                    for accumulated, _delta in agents.stream_refine(contract, user_msg, force_demo=is_demo):
                        raw_acc = accumulated

                    new_contract = agents.parse_draft(raw_acc)
                    st.session_state["contract"] = new_contract
                    st.session_state["critique"] = None
                    placeholder.success("✅ تم تطبيق التعديل بنجاح وتحديث بنود العقد. راجع تبويب الصياغة والمراجعة والتصدير.")
                    st.session_state["chat_history"].append(
                        {"role": "assistant", "content": "تم تعديل بنود العقد بنجاح وتحديث النسخة المعتمدة."}
                    )
                except Exception as e:
                    placeholder.error(f"تعذر التعديل: {e}")


# =============================================================================
# TAB 5 - EXPORT
# =============================================================================
with tab_export:
    st.markdown("### تصدير وطباعة العقد")
    contract: DraftedContract | None = st.session_state.get("contract")

    if contract is None:
        st.warning("يرجى إنشاء العقد أولاً في تبويب «٢. الصياغة الآلية».")
    else:
        st.markdown(
            "يمكنك الآن تحميل المستند بصيغة Word (DOCX) مهيأة بنظام الكتابة من اليمين إلى اليسار (RTL) "
            "أو بصيغة PDF مع تشكيل الحروف العربية، أو كملف نصي خام."
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            try:
                docx_bytes = export.contract_to_docx(contract)
                st.download_button(
                    "📄 تحميل بصيغة DOCX (Word)",
                    data=docx_bytes,
                    file_name="egyptian_contract.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"تعذّر إنشاء DOCX: {e}")

        with c2:
            try:
                pdf_bytes = export.contract_to_pdf(contract)
                st.download_button(
                    "📕 تحميل بصيغة PDF",
                    data=pdf_bytes,
                    file_name="egyptian_contract.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"تعذّر إنشاء PDF: {e}")

        with c3:
            try:
                txt_content = export.contract_to_text(contract)
                st.download_button(
                    "📝 تحميل بصيغة Text",
                    data=txt_content.encode("utf-8"),
                    file_name="egyptian_contract.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"تعذّر إنشاء الملف النصي: {e}")

        st.divider()
        with st.expander("عرض الهيكل البرمجي الموحد (JSON Schema)", expanded=False):
            st.code(contract.model_dump_json(indent=2), language="json")

        st.caption(
            "⚠️ تنويه قانوني: المحتوى المولّد بواسطة الذكاء الاصطناعي يُعد مسودة استرشادية، "
            "وينصح بمراجعته من قِبل محامٍ مقيد بجدول نقابة المحامين المصرية قبل التوقيع النهائي."
        )
