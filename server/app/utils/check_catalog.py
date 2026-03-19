CHECK_CATEGORY_OPTIONS = [
    {
        "code": "admission_record",
        "label": "入院记录与首次病程",
        "templates": [
            "入院记录 24 小时内未完成",
            "主诉、现病史书写不完整",
            "既往史、过敏史记录缺项",
            "首次病程记录缺少诊疗计划",
            "入院评估与病情分级不一致",
        ],
    },
    {
        "code": "course_record",
        "label": "日常病程与上级查房",
        "templates": [
            "日常病程记录不及时",
            "上级医师查房记录缺失",
            "病情变化记录不完整",
            "重要检查结果未及时分析",
            "出入量、生命体征记录与病情不符",
        ],
    },
    {
        "code": "diagnosis_treatment",
        "label": "诊断分析与治疗处置",
        "templates": [
            "诊断依据不充分",
            "鉴别诊断分析缺失",
            "诊疗计划不明确",
            "重要阳性体征未体现到处理意见",
            "治疗调整缺少依据记录",
        ],
    },
    {
        "code": "medical_order",
        "label": "医嘱、检查与用药管理",
        "templates": [
            "长期医嘱开立不规范",
            "临时医嘱执行记录不完整",
            "检查申请与病程记录不一致",
            "抗菌药物使用记录不规范",
            "特殊用药缺少监测记录",
        ],
    },
    {
        "code": "procedure_safety",
        "label": "操作、围手术期与安全管理",
        "templates": [
            "术前讨论记录缺失",
            "手术/操作记录缺项",
            "麻醉相关记录不完整",
            "围手术期交接记录缺失",
            "高风险操作安全核查不完整",
        ],
    },
    {
        "code": "consent_communication",
        "label": "知情同意与医患沟通",
        "templates": [
            "知情同意书签署不完整",
            "病情告知记录不完整",
            "沟通记录与实际处置不一致",
            "自动出院/拒绝检查沟通记录缺失",
            "特殊风险告知记录不完整",
        ],
    },
    {
        "code": "core_system",
        "label": "核心制度与危急值管理",
        "templates": [
            "交接班记录不完整",
            "会诊记录不规范",
            "疑难病例讨论记录缺失",
            "危急值处理记录不完整",
            "死亡病例讨论记录不规范",
        ],
    },
    {
        "code": "discharge_followup",
        "label": "出院记录与随访管理",
        "templates": [
            "出院记录缺项",
            "出院诊断前后不一致",
            "出院医嘱书写不规范",
            "出院带药交代不清晰",
            "随访建议记录不完整",
        ],
    },
    {
        "code": "other",
        "label": "其他问题",
        "templates": [
            "其他未归类问题",
        ],
    },
]

CHECK_CATEGORY_MAP = {item["code"]: item for item in CHECK_CATEGORY_OPTIONS}


def normalize_check_category(category_code):
    return category_code if category_code in CHECK_CATEGORY_MAP else "other"


def get_check_category_label(category_code):
    normalized = normalize_check_category(category_code)
    return CHECK_CATEGORY_MAP[normalized]["label"]


def get_check_template_options(category_code):
    normalized = normalize_check_category(category_code)
    return list(CHECK_CATEGORY_MAP[normalized]["templates"])


def build_check_statistics(items):
    category_stats = []
    doctor_bucket = {}
    summary = {
        "count": len(items),
        "serious": 0,
        "general": 0,
        "rectified": 0,
        "pending": 0,
    }
    category_bucket = {
        option["code"]: {
            "category": option["code"],
            "label": option["label"],
            "count": 0,
            "serious": 0,
            "rectified": 0,
            "pending": 0,
        }
        for option in CHECK_CATEGORY_OPTIONS
    }

    for item in items:
        category_code = normalize_check_category(getattr(item, "issue_category", "other"))
        bucket = category_bucket[category_code]
        bucket["count"] += 1
        if item.severity == "serious":
            summary["serious"] += 1
            bucket["serious"] += 1
        else:
            summary["general"] += 1

        if item.is_rectified:
            summary["rectified"] += 1
            bucket["rectified"] += 1
        else:
            summary["pending"] += 1
            bucket["pending"] += 1

        doctor_id = getattr(item, "responsible_doctor_id", None)
        doctor_name = item.responsible_doctor.real_name if getattr(item, "responsible_doctor", None) else "未指定"
        doctor_stat = doctor_bucket.setdefault(doctor_id or 0, {
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "count": 0,
            "serious": 0,
            "rectified": 0,
            "pending": 0,
        })
        doctor_stat["count"] += 1
        if item.severity == "serious":
            doctor_stat["serious"] += 1
        if item.is_rectified:
            doctor_stat["rectified"] += 1
        else:
            doctor_stat["pending"] += 1

    for option in CHECK_CATEGORY_OPTIONS:
        category_stats.append(category_bucket[option["code"]])

    doctor_stats = sorted(doctor_bucket.values(), key=lambda item: (-item["count"], item["doctor_name"] or ""))
    return {
        "summary": summary,
        "category_stats": category_stats,
        "doctor_stats": doctor_stats,
    }
