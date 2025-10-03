import os
import streamlit as st
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import google.generativeai as genai

# -------------------------------
# Streamlit title
st.title("مولد العقود العربية (Arabic Contract Generator)")

# -------------------------------
# Paths
ARABIC_TEMPLATES_PATH = "./نماذج عقود/مصري - Copy"

# -------------------------------
# Gemini API Configuration
st.sidebar.header("إعدادات Gemini API")
gemini_api_key = "AIzaSyAxyUMN_qQHctU8fTMYByEpxh69BrjJoCQ"

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.warning("⚠️ يرجى إدخال مفتاح Gemini API في الشريط الجانبي")  

# -------------------------------
# Contract type options
contract_types = {
    "عقود البيع": [
        "عقد بيع عقار.docx",
        "عقد بيع محل تجاري.docx", 
        "عقد بيع شقة.docx",
        "عقد بيع سيارة.docx",
        "عقد بيع ابتدائي.docx"
    ],
    "عقود الإيجار": [
        "عقد إيجار محل تجاري.docx",
        "عقد إيجار.docx",
        "عقد إيجار سطح لوضع لافتة إعلانية.docx"
    ],
    "عقود المقاولة": [
        "عقد مقاولة 2.docx",
        "عقد مقاولة مع مهندس لعمل تصميم ومقايسة.docx",
        "عقد مقاولة من الباطن.docx"
    ],
    "عقود الوكالة": [
        "عقد اتفاق مع وكيل بالعمولة.docx"
    ],
    "عقود الهبة": [
        "عقد هبة.docx"
    ],
    "عقود القسمة": [
        "عقد قسمة مع فرز وتجنيب.docx",
        "عقد قسمة وفرز وتجنيب أرض زراعية.docx"
    ],
    "عقود متخصصة": [
        "عقد فرانشيز.docx",
        "عقد طبع ونشر.docx",
        "عقد حفظ سرية و عدم إفصاح ثنائي اللغة.docx",
        "عقد اتعاب محاماه.docx"
    ]
}

# -------------------------------
# Step 1: Contract type selection
contract_category = st.selectbox(
    "اختر نوع العقد", 
    list(contract_types.keys())
)

# -------------------------------
# Step 2: Load templates
documents = []
for file in contract_types[contract_category]:
    file_path = os.path.join(ARABIC_TEMPLATES_PATH, file)
    if os.path.exists(file_path):
        loader = UnstructuredWordDocumentLoader(file_path)
        documents.extend(loader.load())

# -------------------------------
# Step 3: Split into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
docs = text_splitter.split_documents(documents)

# -------------------------------
# Step 4: User input
st.header("أدخل تفاصيل العقد")

col1, col2 = st.columns(2)

with col1:
    party1_name = st.text_input("اسم الطرف الأول")
    party1_address = st.text_area("عنوان الطرف الأول")
    party2_name = st.text_input("اسم الطرف الثاني")
    party2_role = st.selectbox(
        "دور الطرف الثاني", 
        ["مقاول", "مستأجر", "بائع", "مشتري", "وكيل", "مستشار", "أخرى"]
    )
    if party2_role == "أخرى":
        party2_role = st.text_input("حدد الدور")

with col2:
    start_date = st.date_input("تاريخ البداية")
    end_date = st.date_input("تاريخ النهاية")
    jurisdiction = st.text_input("القانون الحاكم")
    contract_value = st.text_input("قيمة العقد (إن وجدت)")
    payment_terms = st.text_input("شروط الدفع")
    special_terms = st.text_area("شروط خاصة (اختياري)")

# -------------------------------
# Step 5: Generate contract
if st.button("إنشاء العقد"):
    if not gemini_api_key:
        st.error("❌ يرجى إدخال مفتاح Gemini API أولاً")
        st.stop()
    
    with st.spinner("جاري إنشاء العقد باستخدام Gemini..."):
        # Embeddings + FAISS
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        if docs:
            vectorstore = FAISS.from_documents(docs, embeddings)
            query = f"{contract_category} عقد نموذج شروط"
            retrieved_docs = vectorstore.similarity_search(query, k=3)
            context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
        else:
            context_text = "نموذج عقد عربي قياسي"

        reference_block = f"""
مراجع من النماذج (للإرشاد فقط، لا تنسخ حرفياً):
{context_text[:1200]}
""".strip()

        # Simplified Arabic prompt template
        prompt_template = f"""اكتب عقد {contract_category} باللغة العربية.

الأطراف:
- الطرف الأول: {party1_name}
- الطرف الثاني: {party2_name} ({party2_role})
- المدة: من {start_date} إلى {end_date}
- القانون الحاكم: {jurisdiction if jurisdiction else 'القوانين المعمول بها'}
- القيمة: {contract_value if contract_value else 'تحدد لاحقاً'}
- الدفع: {payment_terms if payment_terms else 'حسب الاتفاق'}

اكتب عقداً كاملاً ومهنياً يحتوي على:
1. تعريف الأطراف
2. موضوع العقد
3. الالتزامات
4. التعويض
5. السرية
6. الإنهاء
7. القانون الحاكم
8. التوقيعات

العقد:"""

        # Generate contract using Gemini
        try:
            response = model.generate_content(
                prompt_template,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1500,
                    temperature=0.3,
                    top_p=0.8,
                )
            )
            raw_output = response.text
        except Exception as e:
            st.error(f"خطأ في إنشاء العقد: {str(e)}")
            st.stop()

        # Extract only the contract part
        if "العقد:" in raw_output:
            output = raw_output.split("العقد:")[-1].strip()
        else:
            output = raw_output

        st.subheader("العقد المُولد")
        st.text_area("نص العقد", output, height=600)
        st.download_button("تحميل العقد", output, file_name="generated_arabic_contract.txt")
