"""High-fidelity Egyptian Legal Drafting Engine (Offline / Fallback / Demo Mode).

Provides deterministic, legally rigorous contract drafting, strict legal review,
and per-clause chat refinement based on the Egyptian Civil Code (Law 131 of 1948)
and Commercial Code (Law 17 of 1999).

Ensures the application works seamlessly offline or when API limits are reached,
ideal for portfolio demonstrations, local development, and CI testing.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from schema import Article, CritiqueReport, DraftedContract, Party, RedFlag


def generate_offline_contract_json(
    category: str,
    subject: str,
    party1_name: str,
    party1_role: str,
    party1_address: str,
    party2_name: str,
    party2_role: str,
    party2_address: str,
    contract_value: str,
    payment_terms: str,
    start_date: str,
    end_date: str,
    jurisdiction: str,
    special_terms: str,
    rag_snippets: list[str] | None = None,
) -> dict[str, Any]:
    """Synthesize a complete, authentic Egyptian contract data dict."""
    p1 = party1_name or "الطرف الأول"
    p2 = party2_name or "الطرف الثاني"
    p1_r = party1_role or "الطرف الأول"
    p2_r = party2_role or "الطرف الثاني"
    p1_a = party1_address or "جمهورية مصر العربية"
    p2_a = party2_address or "جمهورية مصر العربية"
    val = contract_value or "يحدد لاحقاً بالاتفاق المتبادل"
    pay = payment_terms or "وفقاً للدفعات المتفق عليها بين الطرفين"
    subj = subject or f"التعاقد والاتفاق على تقديم الأعمال والخدمات المشتركة في مجال {category}"
    jur = jurisdiction or "أحكام القانون المدني المصري ومحاكم القاهرة المختصة"
    date_str = start_date or "تاريخ التوقيع"

    # Authentic Egyptian legal articles
    articles = [
        Article(
            number=1,
            title="التمهيد ومحل العقد",
            body=(
                f"يعتبر التمهيد السابق جزءاً لا يتجزأ من هذا العقد وبنداً جوهرياً من بنوده يُفسر معه ويُكمل أحكامه. "
                f"وقد اتفق الطرفان على أن موضوع هذا العقد هو: {subj}، وذلك بكافة الضمانات الفعلية والقانونية "
                f"المستقرة في القانون المصري."
            ),
        ),
        Article(
            number=2,
            title=f"التزامات {p1_r}",
            body=(
                f"يلتزم {p1_r} بتنفيذ التزاماته التعاقدية وفقاً للأصول الفنية والقانونية المتعارف عليها، "
                f"وتسليم كافة المخرجات والمستندات المتعلقة بمحل العقد خالية من أية حقوق عينية أو التزامات للغير، "
                f"مع الالتزام بالجدول الزمني المحدد الذي يبدأ من {date_str} وحتى {end_date or 'إتمام التنفيذ'}."
            ),
        ),
        Article(
            number=3,
            title=f"التزامات {p2_r}",
            body=(
                f"يلتزم {p2_r} بتمكين {p1_r} من أداء مهامه وتوفير كافة البيانات والتسهيلات اللازمة لتنفيذ محل العقد، "
                f"كما يلتزم بسداد المستحقات المالية المقررة في المواعيد المحددة دون تأخير."
            ),
        ),
        Article(
            number=4,
            title="المقابل المالي وطريقة الوفاء",
            body=(
                f"اتفق الطرفان على أن القيمة الإجمالية لهذا العقد هي: ({val})، وتُسدد وفقاً للقواعد والشروط التالية: "
                f"({pay}). ويتم السداد بموجب إيصالات كتابية أو تحويلات بنكية معتمدة على الحساب المصرفي المحدد، "
                f"ويعتبر الإيصال الموقع هو حجة السداد الوحيدة المعترف بها قانوناً."
            ),
        ),
        Article(
            number=5,
            title="المعاينة والتسليم والضمان",
            body=(
                f"يقر {p2_r} بأنه عاين محل العقد المعاينة التامة النافية للجهالة شرعاً وقانوناً، وأنه قبل به بحالته الراهنة. "
                f"ويضمن {p1_r} سلامة التنفيذ وخلو محل التعاقد من أي عيوب خفية وفقاً لأحكام المواد 447 وما بعدها من "
                f"القانون المدني المصري."
            ),
        ),
        Article(
            number=6,
            title="الشرط الجزائي والتعويض الاتفاقي",
            body=(
                f"في حالة إخلال أي من الطرفين بأي التزام من التزاماته الجوهرية الواردة بهذا العقد، أو التأخر في التنفيذ "
                f"عن المواعيد المحددة، يلتزم الطرف المخل بأن يدفع للطرف الآخر تعويضاً اتفاقياً غير خاضع لرقابة القضاء "
                f"قدره 10% من إجمالي قيمة العقد، وذلك دون الإخلال بحق الطرف المتضرر في المطالبة بالتعويض الكامل عن أي "
                f"أضرار فعلية إضافية وفقاً للمادتين 223 و 224 من القانون المدني المصري."
            ),
        ),
        Article(
            number=7,
            title="القوة القاهرة والظروف الطارئة",
            body=(
                "لا يُعتبر أي من الطرفين مخلاً بالتزاماته إذا حال دون تنفيذها حادث مفاجئ أو قوة قاهرة لا يد لأحد الطرفين فيها "
                "ولا يمكن توقعها أو دفعها، طبقاً لأحكام المادة 165 من القانون المدني المصري. ويلتزم الطرف المتأثر بإخطار الطرف "
                "الآخر كتابة فور وقوع الحادث خلال مدة لا تتجاوز 48 ساعة."
            ),
        ),
        Article(
            number=8,
            title="السرية وعدم الإفصاح",
            body=(
                "يتعهد كل طرف بالمحافظة التامة على سرية كافة المعلومات والبيانات والمستندات الفنية والتجارية المتبادلة "
                "بين الطرفين بمناسبة هذا العقد، وعدم إفشائها لأي طرف ثالث أياً كان دون موافقة خطية مسبقة، ويسري هذا "
                "الالتزام طوال مدة العقد ويبقى نافذاً لمدة ثلاث سنوات بعد انتهائه لأي سبب كان."
            ),
        ),
        Article(
            number=9,
            title="الشروط الخاصة المتفق عليها",
            body=(
                f"اتفق الطرفان صراحة على الشروط الإضافية التالية وتعتبر ملزمة لكلا الطرفين: "
                f"{special_terms if special_terms and special_terms.strip() else 'يلتزم الطرفان بمبدأ حسن النية في تنفيذ العقد وفقاً للمادة 148 من القانون المدني المصري.'}"
            ),
        ),
        Article(
            number=10,
            title="فسخ العقد (الشرط الفاسخ الصريح)",
            body=(
                "اتفق الطرفان على أنه في حالة إخلال أحد الطرفين بأي بند من بنود هذا العقد، يعتبر العقد مفسوخاً من تلقاء نفسه "
                "تطبيقاً للمادة 158 من القانون المدني المصري دون حاجة إلى تنبيه أو إنذار أو حكم قضائي، مع حفظ حق الطرف غير المخل "
                "في المطالبة بكافة التعويضات المستحقة."
            ),
        ),
        Article(
            number=11,
            title="القانون الحاكم والاختصاص القضائي",
            body=(
                f"يخضع هذا العقد ويفسر في جميع أحكامه ومنازعاته وفقاً لأحكام {jur}. وتختص المحاكم المصرية بحسب الاختصاص "
                f"النوعي والمكاني بالنظر والفصل في أي نزاع قد ينشأ عن تفسير أو تنفيذ أي بند من بنوده."
            ),
        ),
    ]

    title = f"{category} - {subj[:50]}"
    preamble = (
        f"إنه في يوم الموافق {date_str} بمدينة القاهرة، جمهورية مصر العربية، تم الاتفاق والتراضي بين كل من:\n"
        f"١. السيد/ {p1} ({p1_r}) - المقيم في: {p1_a} (طرف أول)\n"
        f"٢. السيد/ {p2} ({p2_r}) - المقيم في: {p2_a} (طرف ثان)"
    )

    parties_data = [
        {"name": p1, "role": p1_r, "address": p1_a, "national_id": "29001011234567", "representative": ""},
        {"name": p2, "role": p2_r, "address": p2_a, "national_id": "29505051234568", "representative": ""},
    ]

    recitals = [
        f"حيث إن الطرف الأول يمتلك الصلاحية والخبرة في ({subj}) ويرغب في التعاقد بشأنها وفقاً للأصول القانونية المستقرة.",
        "وحيث إن الطرف الثاني قد رغب في التعاقد والارتباط معه بالشروط والضمانات الموضحة أدناه.",
        "وحيث تلاقت إرادتا الطرفين بكامل الأهلية المعتبرة قانوناً للتعاقد والتصرف.",
    ]

    contract_dict = {
        "title": title,
        "preamble": preamble,
        "parties": parties_data,
        "recitals": recitals,
        "subject": subj,
        "articles": [a.model_dump() for a in articles],
        "governing_law": jur,
        "signature_block": "حُرر هذا العقد من نسختين أصليتين، بيد كل طرف نسخة للعمل بموجبها عند اللزوم.",
    }
    return contract_dict


def stream_offline_draft(contract_dict: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Stream JSON tokens with simulated realistic latency for interactive UX."""
    raw_json = json.dumps(contract_dict, ensure_ascii=False, indent=2)
    chunk_size = 40
    acc = ""
    for i in range(0, len(raw_json), chunk_size):
        chunk = raw_json[i : i + chunk_size]
        acc += chunk
        time.sleep(0.01)
        yield acc, chunk


def generate_offline_critique(contract: DraftedContract, client_party: str = "الطرف الأول") -> CritiqueReport:
    """Generate a rigorous legal critique referencing the Egyptian Civil Code."""
    red_flags = [
        RedFlag(
            article_number=6,
            severity="high",
            category="civil_code_violation",
            issue=(
                f"الشرط الجزائي المحدد بنسبة 10% يخضع للسلطة التقديرية للقاضي في التخفيض "
                f"استناداً لنص المادة 224 فقرة 2 من القانون المدني إذا ثبت أن التقدير كان مبالغاً فيه بدرجة كبيرة."
            ),
            suggested_fix=(
                "يُنصح بإضافة عبارة تقرر أن هذا التعويض يمثل اتفاقاً نهائياً غير خاضع لتقدير القضاء "
                "ويعكس الضرر الفعلي المتوقع بما يحمي مصلحة " + client_party + "."
            ),
            civil_code_reference="المادة 224 من القانون المدني المصري رقم 131 لسنة 1948",
        ),
        RedFlag(
            article_number=10,
            severity="critical",
            category="missing_clause",
            issue=(
                "صياغة الشرط الفاسخ الصريح تتطلب استيفاء عبارات الإعفاء من الإعذار بدقة "
                "لتفادي دفع الطرف الآخر بوجوب توجيه إنذار رسمي على يد محضر قبل الفسخ."
            ),
            suggested_fix=(
                "تعديل الصياغة لتصبح: «يعتبر العقد مفسوخاً من تلقاء نفسه دون حاجة إلى تنبيه أو إعذار رسمي "
                "أو اتخاذ أي إجراء قضائي» استناداً للمادة 158 من القانون المدني."
            ),
            civil_code_reference="المادة 158 من القانون المدني المصري",
        ),
        RedFlag(
            article_number=4,
            severity="medium",
            category="vague",
            issue="عدم تحديد موعد نهائي دقيق (تاريخ يوم محدد) لاستحقاق الدفعات اللاحقة وغياب جزاء التأخير في السداد.",
            suggested_fix="تحديد جدول زمني صارم بالتواريخ الميلادية مع فرض فوائد تأخير أو غرامة يومية عن كل يوم تأخير.",
            civil_code_reference="المادة 226 من القانون المدني المصري",
        ),
        RedFlag(
            article_number=8,
            severity="low",
            category="formal_requirement",
            issue="عدم شمول التزام السرية لممثلي الطرفين وموظفيهم وخلفائهم القانونيين صراحة.",
            suggested_fix="النص على سريان التزام السرية على الأطراف وتابعيهم ومساعديهم وخلفهم العام والخاص.",
            civil_code_reference="المادة 145 من القانون المدني وقانون التجارة رقم 17 لسنة 1999",
        ),
    ]

    summary = (
        f"فحص قانوني شامل للعقد استناداً لمصلحة ({client_party}). "
        f"العقد يتمتع ببنية نظامية متكاملة وبنود تغطي الأركان الجوهرية، "
        f"إلا أنه تم رصد ملاحظات قانونية دقيقة في بنود الشرط الجزائي والفسخ الصريح "
        f"يلزم ضبطها لتحصين العقد من الطعن أمام المحاكم المصرية وضمان القوة التنفيذية."
    )

    return CritiqueReport(
        overall_quality="medium",
        summary=summary,
        red_flags=red_flags,
    )


def refine_contract_offline(contract: DraftedContract, user_request: str) -> DraftedContract:
    """Apply intelligent clause modifications based on user chat commands."""
    new_contract = contract.model_copy(deep=True)
    req_lower = user_request.lower()

    if "تحكيم" in user_request or "arbitration" in req_lower:
        # Add or update arbitration clause
        found = False
        for art in new_contract.articles:
            if "تحكيم" in art.title or "فض النزاع" in art.title or "القانون" in art.title:
                art.title = "فض المنازعات والتحكيم التجاري"
                art.body = (
                    "اتفق الطرفان على إحالة أي نزاع أو خلاف ينشأ عن تفسير أو تنفيذ هذا العقد إلى التحكيم التجاري "
                    "وفقاً لقواعد مركز القاهرة الإقليمي للتحكيم التجاري الدولي (CRCICA)، ويكون حكم التحكيم نهائياً "
                    "وملزماً لكلا الطرفين وواجب النفاذ وفقاً لقانون التحكيم المصري رقم 27 لسنة 1994."
                )
                found = True
                break
        if not found:
            new_num = len(new_contract.articles) + 1
            new_contract.articles.append(
                Article(
                    number=new_num,
                    title="شرط التحكيم التجاري الدولي",
                    body=(
                        "يتم فض أي نزاع ينشأ عن هذا العقد بطريق التحكيم لدى مركز القاهرة الإقليمي للتحكيم "
                        "التجاري الدولي (CRCICA) وفقاً لقواعده المعمول بها، وتكون هيئة التحكيم مشكلة من محكم واحد."
                    ),
                )
            )

    elif "شرط جزائي" in user_request or "غرامة" in user_request or "تعويض" in user_request:
        for art in new_contract.articles:
            if "شرط جزائي" in art.title or "التعويض" in art.title:
                art.body = (
                    f"اتفق الطرفان بصورة نهائية وقاطعة على تعديل الشرط الجزائي ليصبح: "
                    f"في حال إخلال أي طرف بالتزاماته، يلتزم بدفع مبلغ تعويض قدره 25% من إجمالي قيمة العقد "
                    f"أو 100,000 جنيه مصري أيهما أكبر، دون حاجة إلى إعذار أو إثبات الضرر عملاً بالمادة 223 مدني."
                )
                break

    elif "فسخ" in user_request:
        for art in new_contract.articles:
            if "فسخ" in art.title:
                art.body = (
                    "يعتبر هذا العقد مفسوخاً حكماً ومن تلقاء نفسه دون حاجة إلى تنبيه أو إعذار رسمي على يد محضر "
                    "أو الحصول على حكم قضائي بمجرد تحقق الإخلال، تطبيقاً لأحكام المادة 158 من القانون المدني المصري."
                )
                break
    else:
        # Generic clause addition
        new_num = len(new_contract.articles) + 1
        new_contract.articles.append(
            Article(
                number=new_num,
                title="بند إضافي معدّل",
                body=f"بناءً على طلب الطرفين: {user_request}. ويلتزم الطرفان بتنفيذه بموجب أحكام هذا العقد.",
            )
        )

    return new_contract
