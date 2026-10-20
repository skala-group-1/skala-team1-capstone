#!/usr/bin/env python3
"""Deterministic mock-data generator for the SKALA capstone (fictional dataset).

All clinic / doctor / user names are FICTIONAL. Nothing here is medical advice.

Usage:
    python3 generate.py --base-date 2026-10-22 --seed 42 --out out/

Outputs:
    out/<table>.json        one JSON array per table
    out/schema.sql          CREATE SCHEMA app + tables + view
    out/V100__seed.sql      INSERT statements (schema app)
    rag_docs/hospitals/     50 generated hospital FAQ markdown docs
"""
import argparse
import datetime as dt
import json
import os
import random
import uuid

KST = dt.timezone(dt.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = "SKALA capstone fictional dataset"
DEMO_PASSWORD = "Passw0rd!"
PASSWORD_PLACEHOLDER = "{bcrypt}PLACEHOLDER"

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

LANGS = ["ko", "en", "zh", "ja"]
LANG_NAME_EN = {"ko": "Korean", "en": "English", "zh": "Chinese", "ja": "Japanese"}
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAME_EN = dict(zip(DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))

# code, category, ko, en, zh, ja, synonyms, duration_min, downtime_days, description_ko, description_en
PROCEDURES = [
    ("JAW_BOTOX", "SKIN", "사각턱 보톡스", "Jaw (Masseter) Botox", "瘦脸针", "エラボトックス",
     ["사각턱 보톡스", "턱보톡스", "masseter botox", "jaw botox", "瘦脸针", "エラボトックス"], 15, 0,
     "저작근에 보툴리눔 톡신을 주입해 턱선을 갸름하게 보이도록 돕는 시술입니다.",
     "Botulinum toxin injected into the masseter muscles to help slim the appearance of the lower face."),
    ("FOREHEAD_BOTOX", "SKIN", "이마 보톡스", "Forehead Botox", "额头肉毒素", "額ボトックス",
     ["이마 주름 보톡스", "forehead botox", "forehead wrinkle botox", "抬头纹肉毒", "額のしわボトックス"], 10, 0,
     "이마 근육의 움직임을 줄여 가로 주름을 완화하는 시술입니다.",
     "Botulinum toxin to soften horizontal forehead lines by relaxing the frontalis muscle."),
    ("LIP_FILLER", "SKIN", "입술 필러", "Lip Filler", "嘴唇玻尿酸", "唇ヒアルロン酸",
     ["입술필러", "lip filler", "lip augmentation", "丰唇", "唇フィラー"], 20, 1,
     "히알루론산 필러로 입술 볼륨과 라인을 보완하는 시술입니다.",
     "Hyaluronic acid filler to add volume and definition to the lips."),
    ("NOSE_FILLER", "SKIN", "코 필러", "Nose Filler", "鼻子玻尿酸", "鼻ヒアルロン酸",
     ["코필러", "nose filler", "non-surgical rhinoplasty", "隆鼻针", "鼻フィラー"], 20, 1,
     "필러로 콧대와 코끝 라인을 비수술적으로 보완하는 시술입니다.",
     "Non-surgical reshaping of the nasal bridge or tip using hyaluronic acid filler."),
    ("REJURAN", "SKIN", "리쥬란 힐러", "Rejuran Healer", "丽珠兰", "リジュラン",
     ["리쥬란", "rejuran", "skin booster", "丽珠兰", "婴儿针", "リジュランヒーラー"], 40, 2,
     "폴리뉴클레오타이드 성분을 피부에 주입해 피부 컨디션 개선을 돕는 스킨부스터입니다.",
     "A polynucleotide-based skin-booster injection aimed at improving skin texture and condition."),
    ("ULTHERAPY", "SKIN", "울쎄라", "Ultherapy", "超声刀", "ウルセラ",
     ["울쎄라 리프팅", "ultherapy", "HIFU lifting", "超声刀", "ウルセラリフト"], 60, 0,
     "고강도 집속 초음파로 피부 깊은 층을 자극해 리프팅 효과를 기대하는 시술입니다.",
     "Microfocused ultrasound treatment targeting deeper skin layers for a lifting effect."),
    ("THERMAGE", "SKIN", "써마지", "Thermage FLX", "热玛吉", "サーマクール",
     ["써마지FLX", "thermage", "RF skin tightening", "热玛吉", "サーマクールFLX"], 60, 0,
     "고주파 에너지로 피부 탄력 개선을 돕는 시술입니다.",
     "Monopolar radiofrequency treatment intended to tighten and firm the skin."),
    ("SHURINK", "SKIN", "슈링크", "Shurink (HIFU)", "舒铃超声提拉", "シュリンク",
     ["슈링크 유니버스", "shurink", "HIFU", "舒铃", "シュリンク"], 30, 0,
     "집속 초음파 장비로 비교적 짧은 시간에 리프팅을 기대하는 시술입니다.",
     "A focused-ultrasound lifting treatment with relatively short treatment time."),
    ("PICO_TONING", "SKIN", "피코토닝", "Pico Toning", "皮秒激光", "ピコトーニング",
     ["피코 레이저", "pico toning", "pico laser", "皮秒", "ピコレーザー"], 20, 0,
     "피코초 레이저로 색소와 피부톤 개선을 돕는 시술입니다.",
     "Picosecond laser toning aimed at pigmentation and uneven skin tone."),
    ("LASER_HAIR_REMOVAL", "SKIN", "레이저 제모", "Laser Hair Removal", "激光脱毛", "レーザー脱毛",
     ["제모", "laser hair removal", "hair removal", "激光脱毛", "医療脱毛"], 30, 0,
     "레이저로 모낭을 표적해 체모를 줄이는 시술로 여러 회차가 필요합니다.",
     "Laser treatment targeting hair follicles to reduce hair growth; multiple sessions are usually needed."),
    ("DOUBLE_EYELID_NONINCISION", "SURGERY", "매몰법 쌍꺼풀", "Non-incisional Double Eyelid", "埋线双眼皮", "埋没法二重",
     ["매몰법", "비절개 쌍꺼풀", "non-incisional double eyelid", "suture double eyelid", "埋线双眼皮", "埋没法"], 40, 5,
     "피부를 절개하지 않고 봉합사로 쌍꺼풀 라인을 만드는 수술입니다.",
     "Creates a double eyelid crease with sutures, without a skin incision."),
    ("DOUBLE_EYELID_INCISION", "SURGERY", "절개법 쌍꺼풀", "Incisional Double Eyelid", "全切双眼皮", "切開法二重",
     ["절개 쌍꺼풀", "incisional double eyelid", "incisional blepharoplasty", "全切双眼皮", "切開法"], 90, 10,
     "눈꺼풀 피부를 절개해 지방·피부를 정리하고 쌍꺼풀 라인을 만드는 수술입니다.",
     "Creates a crease through an eyelid incision, often with removal of excess skin or fat."),
    ("PTOSIS_CORRECTION", "SURGERY", "눈매교정", "Ptosis Correction", "眼睑下垂矫正", "眼瞼下垂手術",
     ["눈매 교정술", "ptosis correction", "eye opening surgery", "眼睑下垂矫正", "眼瞼下垂"], 90, 10,
     "눈을 뜨는 근육의 힘을 보완해 또렷한 눈매를 만드는 수술입니다.",
     "Adjusts the eyelid-lifting muscle to correct drooping lids and open the eyes."),
    ("RHINOPLASTY", "SURGERY", "코성형", "Rhinoplasty", "隆鼻手术", "鼻整形",
     ["코 수술", "rhinoplasty", "nose job", "隆鼻", "鼻整形"], 150, 10,
     "보형물이나 자가 연골을 이용해 코의 모양을 개선하는 수술입니다.",
     "Surgical reshaping of the nose using implants and/or the patient's own cartilage."),
    ("FACIAL_CONTOURING", "SURGERY", "안면윤곽", "Facial Contouring", "面部轮廓手术", "輪郭形成",
     ["윤곽 수술", "광대축소", "facial contouring", "V-line surgery", "削骨", "輪郭手術"], 240, 21,
     "광대·사각턱·턱끝 뼈를 다듬어 얼굴 윤곽을 바꾸는 수술입니다.",
     "Bone surgery on the cheekbones, jaw angle and/or chin to change the facial outline."),
    ("FAT_GRAFTING", "SURGERY", "지방이식", "Fat Grafting", "自体脂肪移植", "脂肪注入",
     ["얼굴 지방이식", "fat grafting", "fat transfer", "脂肪填充", "脂肪注入"], 120, 7,
     "자신의 지방을 채취·정제해 볼륨이 필요한 부위에 이식하는 수술입니다.",
     "Harvests and purifies the patient's own fat and injects it where volume is desired."),
    ("LIPOSUCTION", "SURGERY", "지방흡입", "Liposuction", "吸脂", "脂肪吸引",
     ["지방 흡입술", "liposuction", "lipo", "抽脂", "脂肪吸引"], 150, 7,
     "캐뉼라로 피하지방을 제거해 체형을 다듬는 수술입니다.",
     "Removes subcutaneous fat with a cannula to contour body areas."),
    ("BREAST_AUGMENTATION", "SURGERY", "가슴성형", "Breast Augmentation", "隆胸", "豊胸手術",
     ["가슴 확대", "breast augmentation", "breast implants", "隆胸", "豊胸"], 150, 14,
     "보형물 등을 이용해 가슴 볼륨을 보완하는 수술입니다.",
     "Increases breast volume, typically with implants."),
]
PROC = {p[0]: p for p in PROCEDURES}
SKIN = [p[0] for p in PROCEDURES if p[1] == "SKIN"]
SURGERY = [p[0] for p in PROCEDURES if p[1] == "SURGERY"]
PROC_NAME = {p[0]: {"ko": p[2], "en": p[3], "zh": p[4], "ja": p[5]} for p in PROCEDURES}

# product, dose, price_low, price_high (KRW, rough Seoul ranges)
OPTION_TEMPLATES = {
    "JAW_BOTOX": [("Domestic toxin", "50 units", 30000, 90000), ("Imported toxin", "50 units", 150000, 300000),
                  ("Domestic toxin, 2 sessions", "50 units x 2", 60000, 160000)],
    "FOREHEAD_BOTOX": [("Domestic toxin", "20 units", 30000, 70000), ("Imported toxin", "20 units", 100000, 200000)],
    "LIP_FILLER": [("Domestic HA filler", "1cc", 150000, 300000), ("Imported HA filler", "1cc", 300000, 550000)],
    "NOSE_FILLER": [("Domestic HA filler", "1cc", 150000, 300000), ("Imported HA filler", "1cc", 300000, 500000)],
    "REJURAN": [("Rejuran Healer 2cc", "2cc", 200000, 350000), ("Rejuran Eye 1cc", "1cc", 150000, 250000),
                ("Rejuran Healer 2cc, 3 sessions", "2cc x 3", 550000, 900000)],
    "ULTHERAPY": [("Ultherapy full face", "300 lines", 700000, 1300000),
                  ("Ultherapy full face + neck", "600 lines", 1300000, 2500000)],
    "THERMAGE": [("Thermage FLX full face", "300 shots", 1000000, 1800000),
                 ("Thermage FLX full face", "600 shots", 1800000, 3000000),
                 ("Thermage FLX eyes", "225 shots", 500000, 900000)],
    "SHURINK": [("Shurink Universe", "300 shots", 100000, 250000), ("Shurink Universe", "600 shots", 200000, 400000)],
    "PICO_TONING": [("Pico toning full face", "1 session", 50000, 150000),
                    ("Pico toning package", "5 sessions", 250000, 600000)],
    "LASER_HAIR_REMOVAL": [("Underarms", "5 sessions", 50000, 150000), ("Full face", "1 session", 50000, 120000),
                           ("Full legs", "5 sessions", 400000, 900000)],
    "DOUBLE_EYELID_NONINCISION": [("Natural adhesion (suture) method", "Both eyes", 800000, 1800000),
                                  ("Natural adhesion + epicanthoplasty", "Both eyes", 1500000, 2500000)],
    "DOUBLE_EYELID_INCISION": [("Incisional double eyelid", "Both eyes", 1500000, 3000000),
                               ("Incisional + fat removal", "Both eyes", 2000000, 3500000)],
    "PTOSIS_CORRECTION": [("Non-incisional ptosis correction", "Both eyes", 2000000, 3500000),
                          ("Incisional ptosis correction", "Both eyes", 2500000, 4500000)],
    "RHINOPLASTY": [("Silicone implant + tip plasty", "Full nose", 3000000, 5000000),
                    ("Rib cartilage rhinoplasty", "Full nose", 6000000, 9000000),
                    ("Tip plasty only", "Tip", 1800000, 3000000)],
    "FACIAL_CONTOURING": [("Zygoma reduction", "Both sides", 6000000, 9000000),
                          ("Mandible angle (V-line)", "Both sides", 8000000, 12000000),
                          ("3-point contouring", "Zygoma + mandible + chin", 12000000, 18000000)],
    "FAT_GRAFTING": [("Full face fat grafting", "Full face", 2000000, 4000000),
                     ("Forehead fat grafting", "Forehead", 1500000, 2500000)],
    "LIPOSUCTION": [("Abdomen", "Front + flanks", 3000000, 5000000), ("Thighs", "Inner + outer", 3000000, 5500000),
                    ("Arms", "Both arms", 2000000, 3500000)],
    "BREAST_AUGMENTATION": [("Smooth round implant", "Both breasts", 8000000, 12000000),
                            ("Premium cohesive gel implant", "Both breasts", 10000000, 15000000)],
}

CONDITIONS = [
    ("첫 방문 고객 한정", "First visit only"),
    ("평일 오전 예약 시 적용", "Weekday morning bookings only"),
    ("이벤트 가격, 재시술 시 정상가 적용", "Promotional price; regular price for repeat treatments"),
    ("마취 크림 포함", "Numbing cream included"),
    ("상담 후 최종 금액 확정", "Final price confirmed after consultation"),
    ("사후 관리 1회 포함", "Includes one follow-up care visit"),
]

# area: (count, center lat, lng, gu_ko, gu_en, [(street_ko, street_en)], names ko/en/zh/ja)
AREAS = {
    "GANGNAM": (14, 37.4979, 127.0276, "강남구", "Gangnam-gu",
                [("강남대로", "Gangnam-daero"), ("테헤란로", "Teheran-ro"), ("역삼로", "Yeoksam-ro"), ("봉은사로", "Bongeunsa-ro")],
                {"ko": "강남", "en": "Gangnam", "zh": "江南", "ja": "江南"}),
    "SINSA": (10, 37.5163, 127.0204, "강남구", "Gangnam-gu",
              [("도산대로", "Dosan-daero"), ("논현로", "Nonhyeon-ro"), ("강남대로", "Gangnam-daero")],
              {"ko": "신사", "en": "Sinsa", "zh": "新沙", "ja": "新沙"}),
    "APGUJEONG": (7, 37.5271, 127.0284, "강남구", "Gangnam-gu",
                  [("압구정로", "Apgujeong-ro"), ("논현로", "Nonhyeon-ro"), ("언주로", "Eonju-ro")],
                  {"ko": "압구정", "en": "Apgujeong", "zh": "狎鸥亭", "ja": "狎鴎亭"}),
    "CHEONGDAM": (5, 37.5247, 127.0479, "강남구", "Gangnam-gu",
                  [("선릉로", "Seolleung-ro"), ("도산대로", "Dosan-daero"), ("압구정로", "Apgujeong-ro")],
                  {"ko": "청담", "en": "Cheongdam", "zh": "清潭", "ja": "清潭"}),
    "MYEONGDONG": (8, 37.5636, 126.9827, "중구", "Jung-gu",
                   [("명동길", "Myeongdong-gil"), ("남대문로", "Namdaemun-ro"), ("을지로", "Eulji-ro"), ("퇴계로", "Toegye-ro")],
                   {"ko": "명동", "en": "Myeongdong", "zh": "明洞", "ja": "明洞"}),
    "HONGDAE": (4, 37.5563, 126.9220, "마포구", "Mapo-gu",
                [("양화로", "Yanghwa-ro"), ("와우산로", "Wausan-ro"), ("홍익로", "Hongik-ro")],
                {"ko": "홍대", "en": "Hongdae", "zh": "弘大", "ja": "弘大"}),
    "JAMSIL": (2, 37.5133, 127.1001, "송파구", "Songpa-gu",
               [("올림픽로", "Olympic-ro"), ("송파대로", "Songpa-daero")],
               {"ko": "잠실", "en": "Jamsil", "zh": "蚕室", "ja": "蚕室"}),
}
AREA_ORDER = ["GANGNAM", "SINSA", "APGUJEONG", "CHEONGDAM", "MYEONGDONG", "HONGDAE", "JAMSIL"]

# Invented brand stems (ko, en, zh, ja). Fictional; any resemblance to a real clinic is coincidental.
STEMS = [
    ("루미엘", "Lumiel", "露米艾", "ルミエル"), ("서린", "Seorin", "瑞琳", "ソリン"), ("다온결", "Daongyeol", "多温洁", "ダオンギョル"),
    ("하랑", "Harang", "夏朗", "ハラン"), ("윤슬빛", "Yunseulbit", "允瑟光", "ユンスルビッ"), ("비채", "Bichae", "碧彩", "ビチェ"),
    ("라온제나", "Raonjena", "乐温洁娜", "ラオンジェナ"), ("아리솔", "Arisol", "雅丽松", "アリソル"), ("청아린", "Cheongarin", "清雅琳", "チョンアリン"),
    ("도담솔", "Dodamsol", "道淡松", "ドダムソル"), ("새봄결", "Saebomgyeol", "新春洁", "セボムギョル"), ("가온누리", "Gaonnuri", "佳温努丽", "ガオンヌリ"),
    ("노을빛", "Noeulbit", "霞光", "ノウルビッ"), ("미르엘", "Mirel", "美尔艾", "ミレル"), ("온유담", "Onyudam", "温柔潭", "オニュダム"),
    ("해솔린", "Haesolin", "海松琳", "ヘソリン"), ("나린채", "Narinchae", "娜琳彩", "ナリンチェ"), ("여울담", "Yeouldam", "汝蔚潭", "ヨウルダム"),
    ("보담엘", "Bodamel", "宝潭艾", "ボダメル"), ("시엘로아", "Cieloa", "希艾洛雅", "シエロア"), ("벨루체", "Beluce", "贝露丝", "ベルーチェ"),
    ("리안솔", "Liansol", "丽安松", "リアンソル"), ("소담채", "Sodamchae", "素淡彩", "ソダムチェ"), ("마루엘", "Maruel", "玛如艾", "マルエル"),
    ("한결담", "Hangyeoldam", "韩洁潭", "ハンギョルダム"), ("은솔채", "Eunsolchae", "银松彩", "ウンソルチェ"), ("예담린", "Yedamrin", "艺潭琳", "イェダムリン"),
    ("모아엘", "Moael", "茉雅艾", "モアエル"), ("담율", "Damyul", "潭律", "ダミュル"), ("연우결", "Yeonugyeol", "妍雨洁", "ヨヌギョル"),
    ("초아린", "Choarin", "楚雅琳", "チョアリン"), ("라임솔", "Laimsol", "莱姆松", "ライムソル"), ("하늘결", "Haneulgyeol", "天纹", "ハヌルギョル"),
    ("이든솔", "Idensol", "伊登松", "イドゥンソル"), ("세움채", "Seumchae", "世音彩", "セウムチェ"), ("아라엘", "Arael", "雅拉艾", "アラエル"),
    ("누리안", "Nurian", "努丽安", "ヌリアン"), ("빛나래", "Bitnarae", "光翼", "ビッナレ"), ("솔빛담", "Solbitdam", "松光潭", "ソルビッダム"),
    ("가람채", "Garamchae", "佳蓝彩", "ガラムチェ"), ("라엘린", "Raelin", "拉艾琳", "ラエリン"), ("엘린담", "Ellindam", "艾琳潭", "エリンダム"),
    ("수아결", "Suagyeol", "秀雅洁", "スアギョル"), ("로하엘", "Rohael", "罗哈艾", "ロハエル"), ("비아솔", "Biasol", "碧雅松", "ビアソル"),
    ("오델린", "Odelin", "奥黛琳", "オデリン"), ("펠리체온", "Feliceon", "菲丽切温", "フェリーチェオン"), ("제니엘", "Jeniel", "洁妮尔", "ジェニエル"),
    ("에스린", "Esrin", "艾斯琳", "エスリン"), ("뮤엘담", "Mueldam", "慕艾潭", "ミュエルダム"),
]

CATEGORY_SUFFIX = {
    "DERMA": {"ko": "피부과의원", "en": "Dermatology Clinic", "zh": "皮肤科诊所", "ja": "皮膚科クリニック"},
    "PLASTIC": {"ko": "성형외과의원", "en": "Plastic Surgery Clinic", "zh": "整形外科诊所", "ja": "美容外科クリニック"},
    "BOTH": {"ko": "성형외과·피부과의원", "en": "Plastic Surgery & Dermatology", "zh": "整形皮肤科诊所", "ja": "美容外科・皮膚科クリニック"},
}
CATEGORY_DESC = {
    "DERMA": [
        ("리프팅과 스킨부스터 시술을 중심으로 진료합니다.", "Focuses on lifting and skin-booster treatments.",
         "以提升和皮肤管理项目为主。", "リフティングとスキンブースター施術を中心に診療しています。"),
        ("레이저 토닝과 색소 치료에 강점이 있습니다.", "Known for laser toning and pigmentation care.",
         "擅长激光嫩肤和色素治疗。", "レーザートーニングとシミ治療に力を入れています。"),
        ("보톡스·필러 등 쁘띠 시술을 빠르게 받을 수 있습니다.", "Offers quick injectables such as toxin and filler.",
         "可快速进行肉毒素、玻尿酸等微整形项目。", "ボトックス・フィラーなどのプチ施術を手軽に受けられます。"),
    ],
    "PLASTIC": [
        ("눈·코 성형을 중심으로 1:1 맞춤 상담을 제공합니다.", "Offers one-to-one consultations focused on eye and nose surgery.",
         "以眼鼻整形为主，提供一对一定制咨询。", "目・鼻の整形を中心に1対1のカウンセリングを行っています。"),
        ("안면윤곽과 지방 성형 수술을 진료합니다.", "Performs facial contouring and fat-related procedures.",
         "提供面部轮廓及脂肪相关手术。", "輪郭形成と脂肪関連の手術を行っています。"),
        ("수술 후 회복 관리 프로그램을 운영합니다.", "Runs a post-operative recovery care program.",
         "提供术后恢复管理项目。", "術後のリカバリーケアプログラムを運営しています。"),
    ],
    "BOTH": [
        ("성형 수술과 피부 시술을 한 곳에서 상담할 수 있습니다.", "Consult on both surgery and skin treatments in one place.",
         "可在一处同时咨询整形手术和皮肤项目。", "整形手術と肌施術を一か所で相談できます。"),
        ("외국인 환자를 위한 통역 상담을 운영합니다.", "Provides interpreter-assisted consultations for international patients.",
         "为外国患者提供翻译咨询服务。", "外国人患者向けに通訳付きカウンセリングを行っています。"),
    ],
}
CATEGORY_LABEL = {
    "DERMA": {"ko": "피부과", "en": "dermatology", "zh": "皮肤科", "ja": "皮膚科"},
    "PLASTIC": {"ko": "성형외과", "en": "plastic surgery", "zh": "整形外科", "ja": "美容外科"},
    "BOTH": {"ko": "성형외과·피부과", "en": "plastic surgery & dermatology", "zh": "整形外科及皮肤科", "ja": "美容外科・皮膚科"},
}

OPEN_HOURS_TEMPLATES = [
    {**{d: {"open": "10:00", "close": "19:00"} for d in DAYS[:5]}, "sat": {"open": "10:00", "close": "16:00"}, "sun": None},
    {**{d: {"open": "10:00", "close": "20:00"} for d in DAYS[:5]}, "sat": {"open": "10:00", "close": "17:00"}, "sun": None},
    {**{d: {"open": "09:30", "close": "18:30"} for d in DAYS[:5]}, "sat": {"open": "09:30", "close": "15:00"}, "sun": None},
    {**{d: {"open": "10:00", "close": "19:00"} for d in DAYS[:5]}, "thu": {"open": "10:00", "close": "21:00"},
     "sat": {"open": "10:00", "close": "16:00"}, "sun": {"open": "11:00", "close": "16:00"}},
    {**{d: {"open": "11:00", "close": "20:00"} for d in DAYS[:5]}, "sat": {"open": "11:00", "close": "18:00"},
     "sun": {"open": "11:00", "close": "17:00"}},
]

SURNAMES = [("김", "Kim"), ("이", "Lee"), ("박", "Park"), ("최", "Choi"), ("정", "Jung"), ("강", "Kang"), ("조", "Cho"),
            ("윤", "Yoon"), ("장", "Jang"), ("임", "Lim"), ("한", "Han"), ("오", "Oh"), ("서", "Seo"), ("신", "Shin"),
            ("권", "Kwon"), ("황", "Hwang"), ("안", "Ahn"), ("송", "Song"), ("류", "Ryu"), ("홍", "Hong")]
SYLLABLES = [("민", "min"), ("서", "seo"), ("지", "ji"), ("현", "hyun"), ("준", "jun"), ("우", "woo"), ("예", "ye"),
             ("은", "eun"), ("하", "ha"), ("윤", "yoon"), ("도", "do"), ("수", "su"), ("연", "yeon"), ("재", "jae"),
             ("태", "tae"), ("성", "sung"), ("영", "young"), ("혜", "hye"), ("진", "jin"), ("유", "yu")]
DOCTOR_TITLES = ["대표원장", "원장", "원장", "부원장"]

REJECT_REASONS = [
    "해당 시간에 원장님 수술 일정이 있어 예약이 어렵습니다. 대체 가능한 시간을 확인해 주세요.",
    "요청하신 시술은 대면 상담 후 진행이 필요합니다. 아래 시간 중 상담 예약을 부탁드립니다.",
    "해당 일자 예약이 마감되었습니다. 가능한 다른 시간을 안내드립니다.",
]
CUSTOMER_NOTES = {
    "en": ["First time getting this done, would like a detailed consultation.", "I can only visit in the afternoon.", None],
    "zh": ["第一次做，希望能详细咨询。", "希望有中文翻译。", None],
    "ja": ["初めてなので詳しく相談したいです。", "日本語の通訳をお願いしたいです。", None],
}

# Review templates: REVIEW[lang][sentiment][part]
REVIEW = {
    "ko": {
        "open": ["{area}에서 {proc} 받았어요.", "{proc} 상담부터 시술까지 이곳에서 했습니다.", "지인 추천으로 방문해서 {proc} 했어요."],
        "pos": {"detail": ["결과가 자연스럽고 만족스러워요.", "생각보다 통증이 적었고 붓기도 금방 빠졌어요.", "원장님이 원하는 스타일을 꼼꼼하게 물어봐 주셨어요."],
                "staff": ["상담실장님이 친절하게 설명해 주셨어요.", "대기 시간이 짧아서 좋았어요.", "사후 관리 안내가 자세했어요."],
                "close": ["다음에도 재방문 의사 있어요.", "주변에도 추천하고 싶어요."]},
        "neu": {"detail": ["결과는 무난한 편이에요.", "효과가 기대만큼 크진 않았지만 나쁘지 않아요."],
                "staff": ["대기 시간이 조금 길었어요.", "상담은 무난했어요."],
                "close": ["가격 대비 괜찮은 편입니다.", "한 번 더 받아보고 판단하려고요."]},
        "neg": {"detail": ["기대했던 결과와 달라서 아쉬워요.", "붓기가 생각보다 오래갔어요."],
                "staff": ["상담이 조금 급하게 진행된 느낌이었어요.", "예약 시간보다 많이 기다렸어요."],
                "close": ["재방문은 고민 중입니다.", "다른 곳과 비교해 보고 결정하세요."]},
    },
    "en": {
        "open": ["Got {proc} here while visiting {area}.", "I did my {proc} consultation and treatment at this clinic.",
                 "A friend recommended this place for {proc}."],
        "pos": {"detail": ["The result looks natural and I'm very happy with it.", "Less pain than I expected, and the swelling went down quickly.",
                           "The doctor took time to understand the look I wanted."],
                "staff": ["The interpreter was very helpful.", "Staff explained everything clearly in English.", "Aftercare instructions were detailed."],
                "close": ["Would definitely come back.", "I'd recommend it to friends visiting Seoul."]},
        "neu": {"detail": ["The result is okay, nothing dramatic.", "Effect was a bit less than I hoped, but fine."],
                "staff": ["Waiting time was a little long.", "Communication was okay with some translation gaps."],
                "close": ["Reasonable for the price.", "Might try once more before deciding."]},
        "neg": {"detail": ["The result was not what I expected.", "Swelling lasted longer than I was told."],
                "staff": ["The consultation felt rushed.", "I waited a long time past my appointment."],
                "close": ["Not sure I would return.", "Compare a few clinics before booking."]},
    },
    "zh": {
        "open": ["在{area}做了{proc}。", "从咨询到{proc}都是在这家做的。", "朋友推荐来做{proc}。"],
        "pos": {"detail": ["效果很自然，非常满意。", "比想象中不疼，消肿也很快。", "院长很仔细地询问了我想要的风格。"],
                "staff": ["翻译人员很专业，沟通没有问题。", "咨询师讲解得很耐心。", "术后护理说明很详细。"],
                "close": ["下次还会再来。", "推荐给来首尔的朋友。"]},
        "neu": {"detail": ["效果还可以，比较普通。", "效果没有预期那么明显，但还不错。"],
                "staff": ["等待时间有点长。", "沟通基本顺利。"],
                "close": ["性价比还可以。", "打算再做一次看看。"]},
        "neg": {"detail": ["效果和预期不太一样，有点失望。", "肿胀持续时间比说的要长。"],
                "staff": ["咨询感觉有点匆忙。", "比预约时间等了很久。"],
                "close": ["不太确定会不会再来。", "建议多比较几家再决定。"]},
    },
    "ja": {
        "open": ["{area}で{proc}を受けました。", "{proc}のカウンセリングから施術までこちらでお願いしました。",
                 "友人の紹介で{proc}を受けに来ました。"],
        "pos": {"detail": ["仕上がりが自然でとても満足しています。", "思ったより痛みが少なく、腫れもすぐ引きました。",
                           "先生が希望のデザインを丁寧に聞いてくれました。"],
                "staff": ["通訳の方がいて安心できました。", "スタッフの説明がわかりやすかったです。", "アフターケアの案内が丁寧でした。"],
                "close": ["また利用したいです。", "友人にもすすめたいです。"]},
        "neu": {"detail": ["仕上がりは普通だと思います。", "期待ほどではないですが悪くないです。"],
                "staff": ["待ち時間が少し長かったです。", "説明は一通りしてもらえました。"],
                "close": ["価格相応だと思います。", "もう一度受けてから判断します。"]},
        "neg": {"detail": ["思っていた仕上がりと違って残念です。", "腫れが説明より長く続きました。"],
                "staff": ["カウンセリングが少し急ぎ足でした。", "予約時間よりかなり待ちました。"],
                "close": ["再訪は迷っています。", "いくつか比較してから決めるのがおすすめです。"]},
    },
}
REVIEW_NATIONALITY = {"ko": ["KR"], "en": ["US", "GB", "AU", "CA", "SG"], "zh": ["CN", "TW", "HK", "SG"], "ja": ["JP"]}

GLOSSARY = [
    # procedures
    ("사각턱 보톡스", "jaw botox", "瘦脸针", "エラボトックス", "procedure: JAW_BOTOX"),
    ("이마 보톡스", "forehead botox", "额头肉毒素", "額ボトックス", "procedure: FOREHEAD_BOTOX"),
    ("입술 필러", "lip filler", "嘴唇玻尿酸", "唇ヒアルロン酸", "procedure: LIP_FILLER"),
    ("코 필러", "nose filler", "鼻子玻尿酸", "鼻ヒアルロン酸", "procedure: NOSE_FILLER"),
    ("리쥬란", "Rejuran", "丽珠兰", "リジュラン", "procedure: REJURAN; polynucleotide skin booster"),
    ("울쎄라", "Ultherapy", "超声刀", "ウルセラ", "procedure: ULTHERAPY"),
    ("써마지", "Thermage", "热玛吉", "サーマクール", "procedure: THERMAGE"),
    ("슈링크", "Shurink", "舒铃", "シュリンク", "procedure: SHURINK"),
    ("피코토닝", "pico toning", "皮秒激光", "ピコトーニング", "procedure: PICO_TONING"),
    ("레이저 제모", "laser hair removal", "激光脱毛", "レーザー脱毛", "procedure: LASER_HAIR_REMOVAL"),
    ("매몰법", "non-incisional double eyelid", "埋线双眼皮", "埋没法", "procedure: DOUBLE_EYELID_NONINCISION"),
    ("절개법", "incisional double eyelid", "全切双眼皮", "切開法", "procedure: DOUBLE_EYELID_INCISION"),
    ("눈매교정", "ptosis correction", "眼睑下垂矫正", "眼瞼下垂手術", "procedure: PTOSIS_CORRECTION"),
    ("코성형", "rhinoplasty", "隆鼻手术", "鼻整形", "procedure: RHINOPLASTY"),
    ("안면윤곽", "facial contouring", "面部轮廓手术", "輪郭形成", "procedure: FACIAL_CONTOURING"),
    ("지방이식", "fat grafting", "自体脂肪移植", "脂肪注入", "procedure: FAT_GRAFTING"),
    ("지방흡입", "liposuction", "吸脂", "脂肪吸引", "procedure: LIPOSUCTION"),
    ("가슴성형", "breast augmentation", "隆胸", "豊胸手術", "procedure: BREAST_AUGMENTATION"),
    ("앞트임", "epicanthoplasty", "开眼角", "目頭切開", "often combined with double eyelid surgery"),
    ("쌍꺼풀", "double eyelid", "双眼皮", "二重まぶた", None),
    ("보톡스", "botulinum toxin", "肉毒素", "ボトックス", "generic: botulinum toxin"),
    ("필러", "filler", "玻尿酸", "ヒアルロン酸フィラー", "usually hyaluronic acid"),
    ("스킨부스터", "skin booster", "水光针", "スキンブースター", None),
    ("리프팅", "lifting", "提升", "リフトアップ", None),
    ("보형물", "implant", "假体", "プロテーゼ", None),
    ("자가 연골", "autologous cartilage", "自体软骨", "自家軟骨", "e.g. septal / ear / rib cartilage"),
    ("재수술", "revision surgery", "修复手术", "再手術", None),
    # clinical
    ("붓기", "swelling", "肿胀", "腫れ", None),
    ("멍", "bruising", "淤青", "内出血", None),
    ("통증", "pain", "疼痛", "痛み", None),
    ("흉터", "scar", "疤痕", "傷跡", None),
    ("절개", "incision", "切开", "切開", None),
    ("봉합사", "suture", "缝线", "縫合糸", None),
    ("실밥 제거", "suture removal", "拆线", "抜糸", "typically several days after surgery"),
    ("국소 마취", "local anesthesia", "局部麻醉", "局所麻酔", None),
    ("수면 마취", "IV sedation", "睡眠麻醉", "静脈麻酔", None),
    ("전신 마취", "general anesthesia", "全身麻醉", "全身麻酔", None),
    ("마취 크림", "numbing cream", "麻药膏", "麻酔クリーム", None),
    ("부작용", "side effect", "副作用", "副作用", None),
    ("알레르기", "allergy", "过敏", "アレルギー", None),
    ("항생제", "antibiotic", "抗生素", "抗生物質", None),
    ("진통제", "painkiller", "止痛药", "痛み止め", None),
    ("처방전", "prescription", "处方", "処方箋", None),
    ("혈액 응고 억제제", "blood thinner", "抗凝血药", "抗凝固薬", "inform the doctor before any procedure"),
    ("냉찜질", "cold compress", "冷敷", "冷却", None),
    ("회복 기간", "recovery period", "恢复期", "回復期間", None),
    ("다운타임", "downtime", "恢复期(停工期)", "ダウンタイム", None),
    ("금식", "fasting", "禁食", "絶食", "often required before sedation or general anesthesia"),
    ("임신", "pregnancy", "怀孕", "妊娠", "tell the clinic if pregnant or breastfeeding"),
    # visit / booking
    ("상담", "consultation", "咨询", "カウンセリング", None),
    ("상담실장", "patient coordinator", "咨询师", "カウンセラー", None),
    ("원장", "doctor (clinic director)", "院长", "院長", None),
    ("통역", "interpreter", "翻译", "通訳", None),
    ("예약", "reservation", "预约", "予約", None),
    ("예약금", "deposit", "预约金", "予約金", None),
    ("예약 취소", "cancellation", "取消预约", "予約キャンセル", None),
    ("환불", "refund", "退款", "返金", None),
    ("부가세", "VAT", "增值税", "付加価値税", "Korean VAT is 10%"),
    ("부가세 환급", "VAT refund", "退税", "VAT還付", "eligibility changes; verify with clinic"),
    ("영수증", "receipt", "收据", "領収書", None),
    ("사후 관리", "aftercare", "术后护理", "アフターケア", None),
    ("경과 확인", "follow-up visit", "复诊", "経過観察", None),
    ("동의서", "consent form", "同意书", "同意書", None),
    ("전후 사진", "before & after photos", "术前术后照片", "ビフォーアフター写真", None),
    ("피부과", "dermatology", "皮肤科", "皮膚科", None),
    ("성형외과", "plastic surgery", "整形外科", "美容外科", None),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def iso(t):
    return t.isoformat() if t is not None else None


def kst(d, hh=0, mm=0):
    return dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=KST)


def det_uuid(rng):
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def round_price(rng, v):
    if v >= 1000000:
        return int(round(v / 100000.0)) * 100000
    p = int(round(v / 10000.0)) * 10000
    if rng.random() < 0.3:
        p -= 1000  # e.g. 49,000
    return max(p, 9000)


def korean_name(rng):
    s = rng.choice(SURNAMES)
    a, b = rng.sample(SYLLABLES, 2)
    return s[0] + a[0] + b[0], "%s %s-%s" % (s[1], a[1].capitalize(), b[1])


def hhmm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def gen_procedures():
    rows = []
    for code, cat, ko, en, zh, ja, syn, dur, down, dko, den in PROCEDURES:
        rows.append({"code": code, "category": cat, "name_ko": ko, "name_en": en, "name_zh": zh, "name_ja": ja,
                     "synonyms": syn, "duration_min": dur, "downtime_days": down,
                     "description_ko": dko, "description_en": den})
    return rows


def gen_hospitals(rng, base):
    assert len(STEMS) == 50
    areas = []
    for a in AREA_ORDER:
        areas += [a] * AREAS[a][0]
    # hospitals 1-3 are fixed demo hospitals
    fixed = {1: ("GANGNAM", "BOTH"), 2: ("MYEONGDONG", "DERMA"), 3: ("SINSA", "PLASTIC")}
    for a, _ in fixed.values():
        areas.remove(a)
    rng.shuffle(areas)
    area_by_id = {i: fixed[i][0] for i in fixed}
    for i, a in enumerate(areas, start=4):
        area_by_id[i] = a

    cat_weights = {
        "GANGNAM": (0.3, 0.35, 0.35), "SINSA": (0.15, 0.6, 0.25), "APGUJEONG": (0.15, 0.6, 0.25),
        "CHEONGDAM": (0.5, 0.2, 0.3), "MYEONGDONG": (0.55, 0.15, 0.3), "HONGDAE": (0.6, 0.1, 0.3),
        "JAMSIL": (0.6, 0.2, 0.2),
    }
    stems = STEMS[:]
    rng.shuffle(stems)
    hospitals = []
    for hid in range(1, 51):
        area = area_by_id[hid]
        if hid in fixed:
            cat = fixed[hid][1]
        else:
            cat = rng.choices(["DERMA", "PLASTIC", "BOTH"], weights=cat_weights[area])[0]
        hospitals.append({"id": hid, "area_code": area, "category": cat})

    # guarantee a non-demo Myeongdong surgical clinic for the double-eyelid persona
    myeong = [h for h in hospitals if h["area_code"] == "MYEONGDONG" and h["id"] > 3]
    if not any(h["category"] != "DERMA" for h in myeong):
        myeong[0]["category"] = "BOTH"

    for h in hospitals:
        hid, area, cat = h["id"], h["area_code"], h["category"]
        _, clat, clng, gu_ko, gu_en, streets, _ = AREAS[area]
        stem = stems[hid - 1]
        suf = CATEGORY_SUFFIX[cat]
        street_ko, street_en = rng.choice(streets)
        num, floor = rng.randint(1, 560), rng.randint(2, 15)
        if hid <= 3:
            langs = ["ko", "en", "zh", "ja"]
        else:
            p_zh = 0.8 if area == "MYEONGDONG" else 0.5
            p_ja = 0.7 if area in ("MYEONGDONG", "HONGDAE") else 0.35
            langs = ["ko"] + [l for l, p in (("en", 0.75), ("zh", p_zh), ("ja", p_ja)) if rng.random() < p]
        has_interp = True if hid <= 3 else rng.random() < (0.7 if len(langs) >= 3 else 0.25)
        tmpl = 3 if hid == 1 else (0 if hid == 3 else (4 if hid == 2 else rng.randrange(len(OPEN_HOURS_TEMPLATES))))
        if hid <= 3 or rng.random() > 0.1:
            verified = (base - dt.timedelta(days=rng.randint(3, 180))).isoformat()
        else:
            verified = None
        desc = rng.choice(CATEGORY_DESC[cat])
        an = AREAS[area][6]
        cl = CATEGORY_LABEL[cat]
        h.update({
            "name_ko": "%s %s" % (stem[0], suf["ko"]),
            "name_en": "%s %s" % (stem[1], suf["en"]),
            "name_zh": "%s%s" % (stem[2], suf["zh"]),
            "name_ja": "%s%s" % (stem[3], suf["ja"]),
            "address_ko": "서울특별시 %s %s %d, %d층" % (gu_ko, street_ko, num, floor),
            "address_en": "%dF, %d %s, %s, Seoul" % (floor, num, street_en, gu_en),
            "lat": round(clat + rng.uniform(-0.004, 0.004), 6),
            "lng": round(clng + rng.uniform(-0.004, 0.004), 6),
            "phone": "02-0000-%04d" % (1000 + hid),
            "open_hours": json.loads(json.dumps(OPEN_HOURS_TEMPLATES[tmpl])),
            "supported_languages": langs,
            "has_interpreter": has_interp,
            "verified_at": verified,
            "description_ko": "%s에 위치한 %s 의원입니다. %s" % (an["ko"], cl["ko"], desc[0]),
            "description_en": "A %s clinic in %s. %s" % (cl["en"], an["en"], desc[1]),
            "description_zh": "位于%s的%s诊所。%s" % (an["zh"], cl["zh"], desc[2]),
            "description_ja": "%sにある%sクリニックです。%s" % (an["ja"], cl["ja"], desc[3]),
        })
    order = ["id", "name_ko", "name_en", "name_zh", "name_ja", "category", "area_code", "address_ko", "address_en",
             "lat", "lng", "phone", "open_hours", "supported_languages", "has_interpreter", "verified_at",
             "description_ko", "description_en", "description_zh", "description_ja"]
    return [{k: h[k] for k in order} for h in hospitals]


FIXED_PROCS = {
    1: ["DOUBLE_EYELID_NONINCISION", "DOUBLE_EYELID_INCISION", "PTOSIS_CORRECTION", "RHINOPLASTY", "JAW_BOTOX",
        "FOREHEAD_BOTOX", "LIP_FILLER", "REJURAN", "ULTHERAPY", "SHURINK"],
    2: SKIN[:],
    3: ["DOUBLE_EYELID_NONINCISION", "DOUBLE_EYELID_INCISION", "PTOSIS_CORRECTION", "RHINOPLASTY",
        "FACIAL_CONTOURING", "FAT_GRAFTING", "LIPOSUCTION", "BREAST_AUGMENTATION", "JAW_BOTOX"],
}


def pick_procedures(rng, h, persona):
    if h["id"] in FIXED_PROCS:
        return FIXED_PROCS[h["id"]]
    cat = h["category"]
    if cat == "DERMA":
        procs = rng.sample(SKIN, rng.randint(5, 10))
    elif cat == "PLASTIC":
        procs = rng.sample(SURGERY, rng.randint(4, 7)) + rng.sample(["JAW_BOTOX", "FOREHEAD_BOTOX", "NOSE_FILLER"], rng.randint(1, 2))
    else:
        n = rng.randint(6, 10)
        k = rng.randint(2, n - 2)
        procs = rng.sample(SURGERY, min(k, len(SURGERY))) + rng.sample(SKIN, n - min(k, len(SURGERY)))
    if persona and not any(p.startswith("DOUBLE_EYELID") for p in procs):
        procs.append("DOUBLE_EYELID_NONINCISION")
    order = [p[0] for p in PROCEDURES]
    return sorted(set(procs), key=order.index)


def gen_price_options(rng, hospitals, offered, base):
    rows = []
    for h in hospitals:
        for code in offered[h["id"]]:
            tmpls = OPTION_TEMPLATES[code]
            lo_k = 2 if h["id"] <= 3 and len(tmpls) >= 2 else 1
            for product, dose, lo, hi in rng.sample(tmpls, rng.randint(lo_k, min(3, len(tmpls)))):
                vat = rng.random() < 0.7
                cond = rng.choice(CONDITIONS) if rng.random() < 0.45 else (None, None)
                if not vat and cond[0] is None:
                    cond = ("부가세 10% 별도", "VAT (10%) not included")
                rows.append({
                    "id": len(rows) + 1, "hospital_id": h["id"], "procedure_code": code, "product": product,
                    "dose": dose, "price_krw": round_price(rng, rng.uniform(lo, hi)), "vat_included": vat,
                    "conditions_ko": cond[0], "conditions_en": cond[1],
                    "verified_at": None if (h["id"] > 3 and rng.random() < 0.1)
                    else (base - dt.timedelta(days=rng.randint(1, 120))).isoformat(),
                })
    return rows


def gen_doctors(rng, hospitals, offered):
    rows = []
    for h in hospitals:
        n = 4 if h["id"] <= 3 else rng.randint(2, 4)
        procs = offered[h["id"]]
        specs = [set(rng.sample(procs, min(len(procs), rng.randint(2, 5)))) for _ in range(n)]
        for i, code in enumerate(procs):  # every offered procedure has at least one doctor
            specs[i % n].add(code)
        order = [p[0] for p in PROCEDURES]
        for i in range(n):
            ko, en = korean_name(rng)
            langs = ["ko"] + [l for l in h["supported_languages"][1:] if rng.random() < 0.4]
            if i == 0 and "en" in h["supported_languages"] and "en" not in langs:
                langs.append("en")
            rows.append({
                "id": len(rows) + 1, "hospital_id": h["id"], "name_ko": ko, "name_en": en,
                "title": DOCTOR_TITLES[i], "specialties": sorted(specs[i], key=order.index),
                "languages": [l for l in LANGS if l in langs], "career_years": rng.randint(5, 25),
            })
    return rows


def gen_slots(rng, hospitals, doctors, base, persona_ids):
    docs_by_h = {}
    for d in doctors:
        docs_by_h.setdefault(d["hospital_id"], []).append(d["id"])
    rows = []
    for h in hospitals:
        booked_rate = 0.3 if h["id"] in persona_ids else rng.uniform(0.3, 0.5)
        docs = docs_by_h[h["id"]]
        k = 0
        for day in range(21):
            d = base + dt.timedelta(days=day)
            hours = h["open_hours"][DAYS[d.weekday()]]
            if not hours:
                continue
            start = max(hhmm(hours["open"]), 10 * 60)
            end = min(hhmm(hours["close"]), 18 * 60)
            # round start up to the half hour
            start = (start + 29) // 30 * 30
            t = start
            while t + 30 <= end:
                s = kst(d, t // 60, t % 60)
                rows.append({
                    "id": len(rows) + 1, "hospital_id": h["id"], "doctor_id": docs[k % len(docs)],
                    "start_at": iso(s), "end_at": iso(s + dt.timedelta(minutes=30)),
                    "status": "BOOKED" if rng.random() < booked_rate else "AVAILABLE",
                    "hold_expires_at": None, "version": 0,
                })
                k += 1
                t += 30
    return rows


def gen_users(rng, base):
    customers = [
        ("customer.en1@demo.local", "Emily Carter", "1996-04-12", "F", "US", "en"),
        ("customer.en2@demo.local", "James Whitfield", "1990-09-03", "M", "GB", "en"),
        ("customer.zh1@demo.local", "李晓梅", "1998-02-21", "F", "CN", "zh"),
        ("customer.zh2@demo.local", "陳雨婷", "1994-11-08", "F", "TW", "zh"),
        ("customer.ja1@demo.local", "佐藤遥", "1993-06-17", "F", "JP", "ja"),
        ("customer.ja2@demo.local", "田中健太", "1988-01-30", "M", "JP", "ja"),
    ]
    rows = []

    def add(email, name, birth, gender, nat, locale, role, hid):
        rows.append({
            "id": len(rows) + 1, "email": email, "password_hash": PASSWORD_PLACEHOLDER, "password": DEMO_PASSWORD,
            "name": name, "birth_date": birth, "gender": gender, "nationality": nat, "locale": locale,
            "role": role, "hospital_id": hid,
            "created_at": iso(kst(base - dt.timedelta(days=rng.randint(10, 90)), rng.randint(9, 22), rng.choice([0, 30]))),
        })

    for c in customers:
        add(*c, role="CUSTOMER", hid=None)
    for hid in (1, 2, 3):
        ko, _ = korean_name(rng)
        add("counselor.h%d@demo.local" % hid, ko, "199%d-0%d-1%d" % (hid, hid + 2, hid), "F", "KR", "ko", "COUNSELOR", hid)
        ko, _ = korean_name(rng)
        add("admin.h%d@demo.local" % hid, ko, "198%d-0%d-2%d" % (hid + 2, hid + 4, hid), "M" if hid != 2 else "F",
            "KR", "ko", "HOSPITAL_ADMIN", hid)
    add("operator@demo.local", "운영자", "1989-05-05", "X", "KR", "ko", "OPERATOR", None)
    return rows


def gen_reservations(rng, base, users, hospitals, slots, offered):
    by_h = {}
    for s in slots:
        by_h.setdefault(s["hospital_id"], []).append(s)
    admin_of = {u["hospital_id"]: u["id"] for u in users if u["role"] == "HOSPITAL_ADMIN"}
    customers = [u for u in users if u["role"] == "CUSTOMER"]
    used = set()

    def free_slots(hid, d_from, d_to):
        lo, hi = kst(base + dt.timedelta(days=d_from)), kst(base + dt.timedelta(days=d_to + 1))
        return [s for s in by_h[hid] if s["status"] == "AVAILABLE" and s["id"] not in used
                and lo <= dt.datetime.fromisoformat(s["start_at"]) < hi]

    # (hospital_id, customer index 0-5, status). customer.zh1 (persona) only has one cancelled booking.
    plan = [
        (1, 0, "CONFIRMED"), (1, 1, "PENDING"), (1, 3, "REJECTED"), (1, 4, "CONFIRMED"), (1, 5, "PENDING"),
        (1, 2, "CANCELLED"), (1, 0, "PENDING"), (1, 3, "CONFIRMED"),
        (2, 4, "CONFIRMED"), (2, 3, "PENDING"), (2, 0, "REJECTED"), (2, 5, "CANCELLED"), (2, 1, "CONFIRMED"),
        (3, 1, "PENDING"), (3, 4, "REJECTED"), (3, 0, "CONFIRMED"), (3, 5, "CONFIRMED"),
        (None, 3, "PENDING"), (None, 0, "REJECTED"), (None, 4, "CANCELLED"),
    ]
    others = [h["id"] for h in hospitals if h["id"] > 3 and len(h["supported_languages"]) >= 3]
    rows = []
    for i, (hid, ci, status) in enumerate(plan):
        if hid is None:
            hid = others[i % len(others)]
        user = customers[ci]
        slot = rng.choice(free_slots(hid, 1, 14))
        used.add(slot["id"])
        created = kst(base - dt.timedelta(days=rng.randint(1, 7)), rng.randint(9, 21), rng.choice([0, 10, 25, 40]))
        r = {
            "id": i + 1, "user_id": user["id"], "hospital_id": hid, "slot_id": slot["id"],
            "procedure_code": rng.choice(offered[hid]), "status": status,
            "source": "AI" if rng.random() < 0.6 else "DIRECT", "idempotency_key": det_uuid(rng),
            "customer_note": rng.choice(CUSTOMER_NOTES.get(user["locale"], [None])),
            "reject_reason": None, "alternative_slot_ids": [], "decided_by": None, "decided_at": None,
            "cancelled_at": None, "hold_expires_at": None, "created_at": None, "updated_at": None,
        }
        if status == "PENDING":
            created = kst(base, rng.randint(9, 11), rng.choice([0, 15, 30]))
            r["hold_expires_at"] = iso(created + dt.timedelta(minutes=30))
            slot.update(status="HELD", hold_expires_at=r["hold_expires_at"], version=1)
            updated = created
        elif status == "CONFIRMED":
            updated = created + dt.timedelta(minutes=rng.randint(5, 25))
            r.update(decided_by=admin_of.get(hid), decided_at=iso(updated))
            slot.update(status="BOOKED", version=2)
        elif status == "REJECTED":
            updated = created + dt.timedelta(minutes=rng.randint(5, 25))
            r.update(decided_by=admin_of.get(hid), decided_at=iso(updated), reject_reason=rng.choice(REJECT_REASONS))
            day = (dt.datetime.fromisoformat(slot["start_at"]).date() - base).days
            alts = rng.sample(free_slots(hid, max(1, day - 1), day + 2), 3)
            used.update(a["id"] for a in alts)
            r["alternative_slot_ids"] = sorted(a["id"] for a in alts)
            slot.update(version=2)  # hold released -> AVAILABLE again
        else:  # CANCELLED by the customer after confirmation
            updated = created + dt.timedelta(hours=rng.randint(2, 30))
            r.update(decided_by=admin_of.get(hid), decided_at=iso(created + dt.timedelta(minutes=15)),
                     cancelled_at=iso(updated))
            slot.update(version=3)  # booked -> released
        r["created_at"], r["updated_at"] = iso(created), iso(updated)
        rows.append(r)
    return rows


def gen_reviews(rng, base, hospitals, offered):
    rows = []
    for h in hospitals:
        n = rng.randint(60, 80) if h["id"] <= 3 else rng.randint(5, 80)
        langs = h["supported_languages"]
        lang_w = [4 if l == "ko" else 2 for l in langs]
        an = AREAS[h["area_code"]][6]
        for _ in range(n):
            lang = rng.choices(langs, weights=lang_w)[0]
            code = rng.choice(offered[h["id"]])
            rating = rng.choices([1, 2, 3, 4, 5], weights=[3, 5, 12, 35, 45])[0]
            sent = "pos" if rating >= 4 else ("neu" if rating == 3 else "neg")
            t = REVIEW[lang]
            parts = [rng.choice(t["open"]).format(area=an[lang], proc=PROC_NAME[code][lang])]
            parts += rng.sample(t[sent]["detail"], rng.randint(1, 2))
            parts.append(rng.choice(t[sent]["staff"]))
            parts.append(rng.choice(t[sent]["close"]))
            sep = " " if lang == "en" or lang == "ko" else ""
            created = kst(base - dt.timedelta(days=rng.randint(1, 365)), rng.randint(8, 23), rng.randint(0, 59))
            rows.append({
                "id": len(rows) + 1, "hospital_id": h["id"], "user_id": None, "procedure_code": code,
                "rating": rating,
                "age_group": rng.choices(["20s", "30s", "40s", "50s"], weights=[35, 35, 20, 10])[0],
                "gender": rng.choices(["F", "M", "X"], weights=[75, 23, 2])[0],
                "reviewer_nationality": rng.choice(REVIEW_NATIONALITY[lang]), "lang": lang,
                "content": sep.join(parts), "created_at": iso(created),
            })
    return rows


def gen_glossary():
    return [{"id": i + 1, "term_ko": g[0], "term_en": g[1], "term_zh": g[2], "term_ja": g[3], "note": g[4]}
            for i, g in enumerate(GLOSSARY)]


def gen_consultations(rng, base, users, price_options, slots):
    counselor_h1 = next(u for u in users if u["email"] == "counselor.h1@demo.local")
    zh1 = next(u for u in users if u["email"] == "customer.zh1@demo.local")
    ja1 = next(u for u in users if u["email"] == "customer.ja1@demo.local")
    price = min(p["price_krw"] for p in price_options
                if p["hospital_id"] == 1 and p["procedure_code"] == "DOUBLE_EYELID_NONINCISION")
    day_from, day_to = base + dt.timedelta(days=1), base + dt.timedelta(days=7)
    conv_wait, conv_active = det_uuid(rng), det_uuid(rng)
    t_wait = kst(base, 9, 40)
    t_active = kst(base, 9, 5)

    conversations = [
        {"id": conv_active, "user_id": zh1["id"], "parent_conversation_id": None, "mode": "HUMAN", "selected_hospital_id": 1, "consultation_id": 1,
         "created_at": iso(t_active - dt.timedelta(minutes=12))},
        {"id": conv_wait, "user_id": ja1["id"], "parent_conversation_id": None, "mode": "HUMAN", "selected_hospital_id": 1, "consultation_id": 2,
         "created_at": iso(t_wait - dt.timedelta(minutes=8))},
    ]
    consultations = [
        {"id": 1, "user_id": zh1["id"], "hospital_id": 1, "counselor_id": counselor_h1["id"],
         "conversation_id": conv_active, "status": "ACTIVE", "customer_locale": "zh",
         "summary_card": {"procedure_code": "DOUBLE_EYELID_NONINCISION", "procedure_name": "埋线双眼皮",
                          "preferred_areas": ["GANGNAM", "MYEONGDONG"],
                          "preferred_dates": [day_from.isoformat(), day_to.isoformat()],
                          "concerns": ["恢复期", "回国航班时间", "价格是否含税"], "language": "zh"},
         "summary_card_ko": {"procedure_code": "DOUBLE_EYELID_NONINCISION", "procedure_name": "매몰법 쌍꺼풀",
                             "preferred_areas": ["강남", "명동"],
                             "preferred_dates": [day_from.isoformat(), day_to.isoformat()],
                             "concerns": ["회복 기간", "귀국 비행 일정", "부가세 포함 여부"], "language": "zh"},
         "consent_at": iso(t_active - dt.timedelta(minutes=1)), "created_at": iso(t_active), "closed_at": None},
        {"id": 2, "user_id": ja1["id"], "hospital_id": 1, "counselor_id": None,
         "conversation_id": conv_wait, "status": "WAITING", "customer_locale": "ja",
         "summary_card": {"procedure_code": "JAW_BOTOX", "procedure_name": "エラボトックス",
                          "preferred_areas": ["GANGNAM"], "preferred_dates": [day_from.isoformat(), day_from.isoformat()],
                          "concerns": ["効果の持続期間", "日本語の通訳"], "language": "ja"},
         "summary_card_ko": {"procedure_code": "JAW_BOTOX", "procedure_name": "사각턱 보톡스",
                             "preferred_areas": ["강남"], "preferred_dates": [day_from.isoformat(), day_from.isoformat()],
                             "concerns": ["효과 지속 기간", "일본어 통역"], "language": "ja"},
         "consent_at": iso(t_wait - dt.timedelta(minutes=1)), "created_at": iso(t_wait), "closed_at": None},
    ]
    p = "{:,}".format(price)
    msgs = [
        ("CUSTOMER", "zh", "您好，我想咨询一下埋线双眼皮。下周可以预约吗？",
         "안녕하세요, 매몰법 쌍꺼풀 상담을 받고 싶어요. 다음 주에 예약이 가능할까요?", {"glossary_hits": ["埋线双眼皮=매몰법"]}),
        ("COUNSELOR", "ko", "안녕하세요! 네, 다음 주 화요일과 목요일 오후에 상담 가능한 시간이 있습니다. 원하시는 날짜가 있으신가요?",
         "您好！是的，下周二和周四下午有可以面诊的时间。您有希望的日期吗？", {}),
        ("CUSTOMER", "zh", "周四下午比较好。手术后多久可以坐飞机回国？",
         "목요일 오후가 좋아요. 수술 후 얼마나 지나야 비행기를 타고 귀국할 수 있나요?", {}),
        ("COUNSELOR", "ko", "개인차가 있지만 매몰법은 보통 수술 후 며칠 내 비행하는 경우가 많습니다. 정확한 일정은 원장님 진료 시 확인해 주세요.",
         "虽然因人而异，但埋线法通常在术后几天内乘坐飞机的情况较多。具体日程请在院长面诊时确认。",
         {"medical_content": True, "glossary_hits": ["매몰법=埋线法"]}),
        ("CUSTOMER", "zh", "好的。价格大概是多少？包含增值税吗？",
         "알겠습니다. 가격은 대략 얼마인가요? 부가세 포함인가요?", {"glossary_hits": ["增值税=부가세"]}),
        ("COUNSELOR", "ko", "매몰법 양쪽 기준 %s원부터이며, 최종 금액은 상담 후 확정됩니다. 예약 요청을 남겨주시면 병원 확인 후 확정됩니다." % p,
         "埋线法双眼起价%s韩元，最终价格将在面诊后确定。提交预约申请后，经医院确认即可确定预约。" % p, {"price_quote": True}),
    ]
    chat = []
    t = t_active + dt.timedelta(minutes=1)
    for role, lang, orig, trans, flags in msgs:
        chat.append({
            "id": len(chat) + 1, "consultation_id": 1,
            "sender_id": zh1["id"] if role == "CUSTOMER" else counselor_h1["id"], "sender_role": role,
            "original_text": orig, "original_lang": lang, "translated_text": trans,
            "translated_lang": "ko" if lang == "zh" else "zh", "translation_status": "DONE",
            "flags": flags, "created_at": iso(t),
        })
        t += dt.timedelta(minutes=rng.randint(1, 3))
    return conversations, consultations, chat


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """-- SKALA capstone fictional dataset: schema
-- Fictional educational data. Not medical advice.
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid() on PG < 13
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector, for rag.chunks.embedding

CREATE TABLE app.hospitals (
    id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name_ko             varchar(200) NOT NULL,
    name_en             varchar(200) NOT NULL,
    name_zh             varchar(200),
    name_ja             varchar(200),
    category            varchar(10)  NOT NULL CHECK (category IN ('DERMA','PLASTIC','BOTH')),
    area_code           varchar(20)  NOT NULL CHECK (area_code IN ('GANGNAM','SINSA','APGUJEONG','CHEONGDAM','MYEONGDONG','HONGDAE','JAMSIL')),
    address_ko          varchar(300),
    address_en          varchar(300),
    lat                 numeric(9,6),
    lng                 numeric(9,6),
    phone               varchar(30),
    open_hours          jsonb        NOT NULL DEFAULT '{}'::jsonb,
    supported_languages text[]       NOT NULL DEFAULT ARRAY['ko']::text[],
    has_interpreter     boolean      NOT NULL DEFAULT false,
    verified_at         date,
    description_ko      text,
    description_en      text,
    description_zh      text,
    description_ja      text
);
CREATE INDEX idx_hospitals_area ON app.hospitals (area_code);
CREATE INDEX idx_hospitals_langs ON app.hospitals USING gin (supported_languages);

CREATE TABLE app.users (
    id            bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    email         varchar(255) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    name          varchar(100) NOT NULL,
    birth_date    date,
    gender        char(1)      CHECK (gender IN ('F','M','X')),
    nationality   char(2),
    locale        varchar(5)   NOT NULL DEFAULT 'en' CHECK (locale IN ('en','zh','ja','ko')),
    role          varchar(20)  NOT NULL CHECK (role IN ('CUSTOMER','COUNSELOR','HOSPITAL_ADMIN','OPERATOR')),
    hospital_id   bigint       REFERENCES app.hospitals(id),
    created_at    timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE app.procedures (
    code           varchar(40) PRIMARY KEY,
    category       varchar(10) NOT NULL CHECK (category IN ('SKIN','SURGERY')),
    name_ko        varchar(100) NOT NULL,
    name_en        varchar(100) NOT NULL,
    name_zh        varchar(100),
    name_ja        varchar(100),
    synonyms       text[]  NOT NULL DEFAULT '{}'::text[],
    duration_min   integer,
    downtime_days  integer,
    description_ko text,
    description_en text
);
CREATE INDEX idx_procedures_synonyms ON app.procedures USING gin (synonyms);

CREATE TABLE app.doctors (
    id           bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    hospital_id  bigint NOT NULL REFERENCES app.hospitals(id),
    name_ko      varchar(50) NOT NULL,
    name_en      varchar(100),
    title        varchar(50),
    specialties  text[] NOT NULL DEFAULT '{}'::text[],
    languages    text[] NOT NULL DEFAULT ARRAY['ko']::text[],
    career_years integer
);
CREATE INDEX idx_doctors_hospital ON app.doctors (hospital_id);

CREATE TABLE app.price_options (
    id             bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    hospital_id    bigint NOT NULL REFERENCES app.hospitals(id),
    procedure_code varchar(40) NOT NULL REFERENCES app.procedures(code),
    product        varchar(200) NOT NULL,
    dose           varchar(100),
    price_krw      integer NOT NULL CHECK (price_krw >= 0),
    vat_included   boolean NOT NULL DEFAULT true,
    conditions_ko  text,
    conditions_en  text,
    verified_at    date
);
CREATE INDEX idx_price_options_hospital ON app.price_options (hospital_id);
CREATE INDEX idx_price_options_procedure ON app.price_options (procedure_code, price_krw);

CREATE TABLE app.slots (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    hospital_id     bigint NOT NULL REFERENCES app.hospitals(id),
    doctor_id       bigint REFERENCES app.doctors(id),
    start_at        timestamptz NOT NULL,
    end_at          timestamptz NOT NULL,
    status          varchar(10) NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE','HELD','BOOKED')),
    hold_expires_at timestamptz,
    version         integer NOT NULL DEFAULT 0,
    UNIQUE (hospital_id, start_at),
    CHECK (end_at > start_at)
);
CREATE INDEX idx_slots_hospital_status_start ON app.slots (hospital_id, status, start_at);

CREATE TABLE app.reservations (
    id                   bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id              bigint NOT NULL REFERENCES app.users(id),
    hospital_id          bigint NOT NULL REFERENCES app.hospitals(id),
    slot_id              bigint NOT NULL REFERENCES app.slots(id),
    procedure_code       varchar(40) NOT NULL REFERENCES app.procedures(code),
    status               varchar(10) NOT NULL CHECK (status IN ('PENDING','CONFIRMED','REJECTED','CANCELLED')),
    source               varchar(10) NOT NULL DEFAULT 'DIRECT' CHECK (source IN ('AI','DIRECT')),
    idempotency_key      uuid NOT NULL UNIQUE,
    customer_note        text,
    reject_reason        text,
    alternative_slot_ids bigint[] NOT NULL DEFAULT '{}'::bigint[],
    decided_by           bigint REFERENCES app.users(id),
    decided_at           timestamptz,
    cancelled_at         timestamptz,
    hold_expires_at      timestamptz,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_reservations_user ON app.reservations (user_id, created_at DESC);
CREATE INDEX idx_reservations_hospital_status ON app.reservations (hospital_id, status);
-- at most one active (PENDING/CONFIRMED) reservation per slot
CREATE UNIQUE INDEX uq_reservations_active_slot ON app.reservations (slot_id) WHERE status IN ('PENDING','CONFIRMED');

CREATE TABLE app.reviews (
    id                   bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    hospital_id          bigint NOT NULL REFERENCES app.hospitals(id),
    user_id              bigint REFERENCES app.users(id),
    procedure_code       varchar(40) REFERENCES app.procedures(code),
    rating               smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    age_group            varchar(5) CHECK (age_group IN ('20s','30s','40s','50s')),
    gender               char(1) CHECK (gender IN ('F','M','X')),
    reviewer_nationality char(2),
    lang                 varchar(5) NOT NULL CHECK (lang IN ('ko','en','zh','ja')),
    content              text NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_reviews_hospital ON app.reviews (hospital_id);

CREATE TABLE app.glossary (
    id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    term_ko varchar(100) NOT NULL,
    term_en varchar(100),
    term_zh varchar(100),
    term_ja varchar(100),
    note    text
);

CREATE TABLE app.conversations (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                bigint NOT NULL REFERENCES app.users(id),
    parent_conversation_id uuid REFERENCES app.conversations(id),
    mode                 varchar(10) NOT NULL DEFAULT 'MAIN' CHECK (mode IN ('MAIN','HOSPITAL','HUMAN')),
    selected_hospital_id bigint REFERENCES app.hospitals(id),
    consultation_id      bigint,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.ai_tasks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid REFERENCES app.conversations(id),
    user_id         bigint REFERENCES app.users(id),
    input           text NOT NULL,
    status          varchar(20) NOT NULL DEFAULT 'QUEUED',
    answer          text,
    sources         jsonb,
    pending_action  jsonb,
    attempts        integer NOT NULL DEFAULT 0,
    error           text,
    trace_url       text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz
);
CREATE INDEX idx_ai_tasks_conversation ON app.ai_tasks (conversation_id, created_at);

CREATE TABLE app.consultations (
    id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id          bigint NOT NULL REFERENCES app.users(id),
    hospital_id      bigint NOT NULL REFERENCES app.hospitals(id),
    counselor_id     bigint REFERENCES app.users(id),
    conversation_id  uuid REFERENCES app.conversations(id) DEFERRABLE INITIALLY DEFERRED,
    status           varchar(10) NOT NULL DEFAULT 'WAITING' CHECK (status IN ('WAITING','ACTIVE','CLOSED')),
    customer_locale  varchar(5),
    summary_card     jsonb,
    summary_card_ko  jsonb,
    consent_at       timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now(),
    closed_at        timestamptz
);
CREATE INDEX idx_consultations_hospital_status ON app.consultations (hospital_id, status);

ALTER TABLE app.conversations
    ADD CONSTRAINT fk_conversations_consultation FOREIGN KEY (consultation_id)
    REFERENCES app.consultations(id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE app.chat_messages (
    id                 bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    consultation_id    bigint NOT NULL REFERENCES app.consultations(id),
    sender_id          bigint REFERENCES app.users(id),
    sender_role        varchar(20) NOT NULL,
    original_text      text NOT NULL,
    original_lang      varchar(5),
    translated_text    text,
    translated_lang    varchar(5),
    translation_status varchar(10) NOT NULL DEFAULT 'PENDING',
    flags              jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_messages_consultation ON app.chat_messages (consultation_id, created_at);

CREATE TABLE app.notifications (
    id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id    bigint NOT NULL REFERENCES app.users(id),
    type       varchar(50) NOT NULL,
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    read_at    timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON app.notifications (user_id, created_at DESC);

CREATE TABLE app.audit_logs (
    id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    trace_id   varchar(64),
    actor_id   bigint,
    actor_role varchar(20),
    action     varchar(50) NOT NULL,
    target     varchar(100),
    detail     jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_logs_trace ON app.audit_logs (trace_id);

CREATE TABLE app.refresh_tokens (
    id          bigserial PRIMARY KEY,
    user_id     bigint NOT NULL REFERENCES app.users(id),
    token_hash  text NOT NULL UNIQUE,
    family_id   uuid NOT NULL,
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz,
    replaced_by bigint REFERENCES app.refresh_tokens(id),
    user_agent  text,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_tokens_user ON app.refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_family ON app.refresh_tokens (family_id);

CREATE TABLE rag.documents (
    doc_id         text PRIMARY KEY,
    title          text NOT NULL,
    doc_type       varchar(20) NOT NULL CHECK (doc_type IN ('GUIDE','PREP','AFTERCARE','FAQ','TRAVEL','HOSPITAL_FAQ')),
    procedure_code varchar(40) REFERENCES app.procedures(code),
    hospital_id    bigint REFERENCES app.hospitals(id),
    lang           varchar(5) NOT NULL DEFAULT 'en',
    source         text,
    version        integer NOT NULL DEFAULT 1,
    body           text NOT NULL
);
CREATE INDEX idx_rag_documents_type ON rag.documents (doc_type);

CREATE TABLE rag.chunks (
    chunk_id        bigserial PRIMARY KEY,
    doc_id          text NOT NULL REFERENCES rag.documents(doc_id) ON DELETE CASCADE,
    section         text,
    text            text NOT NULL,
    embedding       vector(1536),
    embedding_model text,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_rag_chunks_doc ON rag.chunks (doc_id);

CREATE VIEW app.hospital_review_stats AS
SELECT h.id                                              AS hospital_id,
       count(r.id)                                       AS review_count,
       round(avg(r.rating)::numeric, 2)                  AS avg_rating,
       count(r.id) FILTER (WHERE r.age_group = '20s')    AS age_20s_count,
       count(r.id) FILTER (WHERE r.age_group = '30s')    AS age_30s_count,
       count(r.id) FILTER (WHERE r.age_group = '40s')    AS age_40s_count,
       count(r.id) FILTER (WHERE r.age_group = '50s')    AS age_50s_count,
       count(r.id) FILTER (WHERE r.gender = 'F')         AS female_count,
       count(r.id) FILTER (WHERE r.gender = 'M')         AS male_count,
       count(r.id) FILTER (WHERE r.gender = 'X')         AS other_gender_count
FROM app.hospitals h
LEFT JOIN app.reviews r ON r.hospital_id = h.id
GROUP BY h.id;
"""

# column -> SQL kind. Only columns listed here are inserted (e.g. users.password stays JSON-only).
COLUMNS = {
    "hospitals": {"id": "int", "name_ko": "text", "name_en": "text", "name_zh": "text", "name_ja": "text",
                  "category": "text", "area_code": "text", "address_ko": "text", "address_en": "text",
                  "lat": "num", "lng": "num", "phone": "text", "open_hours": "jsonb",
                  "supported_languages": "text[]", "has_interpreter": "bool", "verified_at": "text",
                  "description_ko": "text", "description_en": "text", "description_zh": "text",
                  "description_ja": "text"},
    "users": {"id": "int", "email": "text", "password_hash": "text", "name": "text", "birth_date": "text",
              "gender": "text", "nationality": "text", "locale": "text", "role": "text", "hospital_id": "int",
              "created_at": "text"},
    "procedures": {"code": "text", "category": "text", "name_ko": "text", "name_en": "text", "name_zh": "text",
                   "name_ja": "text", "synonyms": "text[]", "duration_min": "int", "downtime_days": "int",
                   "description_ko": "text", "description_en": "text"},
    "doctors": {"id": "int", "hospital_id": "int", "name_ko": "text", "name_en": "text", "title": "text",
                "specialties": "text[]", "languages": "text[]", "career_years": "int"},
    "price_options": {"id": "int", "hospital_id": "int", "procedure_code": "text", "product": "text", "dose": "text",
                      "price_krw": "int", "vat_included": "bool", "conditions_ko": "text", "conditions_en": "text",
                      "verified_at": "text"},
    "slots": {"id": "int", "hospital_id": "int", "doctor_id": "int", "start_at": "text", "end_at": "text",
              "status": "text", "hold_expires_at": "text", "version": "int"},
    "reviews": {"id": "int", "hospital_id": "int", "user_id": "int", "procedure_code": "text", "rating": "int",
                "age_group": "text", "gender": "text", "reviewer_nationality": "text", "lang": "text",
                "content": "text", "created_at": "text"},
    "glossary": {"id": "int", "term_ko": "text", "term_en": "text", "term_zh": "text", "term_ja": "text",
                 "note": "text"},
    "conversations": {"id": "uuid", "user_id": "int", "parent_conversation_id": "uuid", "mode": "text", "selected_hospital_id": "int",
                      "consultation_id": "int", "created_at": "text"},
    "consultations": {"id": "int", "user_id": "int", "hospital_id": "int", "counselor_id": "int",
                      "conversation_id": "uuid", "status": "text", "customer_locale": "text",
                      "summary_card": "jsonb", "summary_card_ko": "jsonb", "consent_at": "text",
                      "created_at": "text", "closed_at": "text"},
    "chat_messages": {"id": "int", "consultation_id": "int", "sender_id": "int", "sender_role": "text",
                      "original_text": "text", "original_lang": "text", "translated_text": "text",
                      "translated_lang": "text", "translation_status": "text", "flags": "jsonb",
                      "created_at": "text"},
    "reservations": {"id": "int", "user_id": "int", "hospital_id": "int", "slot_id": "int",
                     "procedure_code": "text", "status": "text", "source": "text", "idempotency_key": "uuid",
                     "customer_note": "text", "reject_reason": "text", "alternative_slot_ids": "bigint[]",
                     "decided_by": "int", "decided_at": "text", "cancelled_at": "text",
                     "hold_expires_at": "text", "created_at": "text", "updated_at": "text"},
}
INSERT_ORDER = ["hospitals", "users", "procedures", "doctors", "price_options", "slots", "reviews", "glossary",
                "conversations", "consultations", "chat_messages", "reservations"]
IDENTITY_TABLES = ["hospitals", "users", "doctors", "price_options", "slots", "reviews", "glossary",
                   "consultations", "chat_messages", "reservations"]
EMPTY_TABLES = ["ai_tasks", "notifications", "audit_logs", "refresh_tokens"]


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def sql_value(v, kind):
    if v is None:
        return "NULL"
    if kind == "int":
        return str(int(v))
    if kind == "num":
        return repr(float(v))
    if kind == "bool":
        return "TRUE" if v else "FALSE"
    if kind == "jsonb":
        return q(json.dumps(v, ensure_ascii=False, sort_keys=True)) + "::jsonb"
    if kind == "uuid":
        return q(v) + "::uuid"
    if kind == "text[]":
        return "ARRAY[" + ",".join(q(x) for x in v) + "]::text[]" if v else "'{}'::text[]"
    if kind == "bigint[]":
        return "ARRAY[" + ",".join(str(int(x)) for x in v) + "]::bigint[]" if v else "'{}'::bigint[]"
    return q(v)


def build_seed_sql(data, base, seed):
    out = ["-- SKALA capstone fictional dataset: seed data (base-date %s, seed %d)" % (base.isoformat(), seed),
           "-- Fictional educational data. Not medical advice. Generated by data/mock/generate.py",
           "-- users.password_hash is a placeholder; the backend seeder must re-hash 'Passw0rd!' with BCrypt.",
           "SET client_encoding = 'UTF8';",
           "BEGIN;", ""]
    for table in INSERT_ORDER:
        rows = data[table]
        if not rows:
            continue
        cols = list(COLUMNS[table])
        for i in range(0, len(rows), 500):
            out.append("INSERT INTO app.%s (%s) VALUES" % (table, ", ".join(cols)))
            chunk = rows[i:i + 500]
            lines = ["(" + ", ".join(sql_value(r[c], COLUMNS[table][c]) for c in cols) + ")" for r in chunk]
            out.append(",\n".join(lines) + ";")
            out.append("")
    out.append("-- advance identity sequences past explicit ids")
    for table in IDENTITY_TABLES:
        out.append("SELECT setval(pg_get_serial_sequence('app.%s', 'id'), "
                   "GREATEST((SELECT COALESCE(max(id), 0) FROM app.%s), 1));" % (table, table))
    out += ["", "COMMIT;", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Hospital FAQ docs
# ---------------------------------------------------------------------------


def hospital_faq(h, docs, options):
    hid = h["id"]
    an = AREAS[h["area_code"]][6]["en"]
    langs = ", ".join(LANG_NAME_EN[l] for l in h["supported_languages"])
    lines = [
        "---",
        "doc_id: HOSPITAL_FAQ_%03d" % hid,
        'title: "%s — Visitor FAQ"' % h["name_en"],
        "doc_type: HOSPITAL_FAQ",
        "hospital_id: %d" % hid,
        "lang: en",
        'source: "%s"' % SOURCE,
        "version: 1",
        "---",
        "",
        "> Fictional educational content. Not medical advice.",
        "",
        "# %s (%s)" % (h["name_en"], h["name_ko"]),
        "",
        "%s" % h["description_en"],
        "",
        "## Where is the clinic?",
        "",
        "%s is in the %s area of Seoul." % (h["name_en"], an),
        "",
        "- Address (EN): %s" % h["address_en"],
        "- Address (KO): %s" % h["address_ko"],
        "- Phone: %s (fictional number)" % h["phone"],
        "",
        "## What are the opening hours?",
        "",
        "| Day | Hours |",
        "| --- | --- |",
    ]
    for d in DAYS:
        oh = h["open_hours"][d]
        lines.append("| %s | %s |" % (DAY_NAME_EN[d], "%s–%s" % (oh["open"], oh["close"]) if oh else "Closed"))
    lines += [
        "",
        "Hours may change on Korean public holidays; please check with the clinic before visiting.",
        "",
        "## Which languages are supported?",
        "",
        "Consultations are available in: %s." % langs,
        "",
        "## Is an interpreter available?",
        "",
        ("Yes. The clinic has interpreter support for international patients. Ask for an interpreter when "
         "you request a reservation." if h["has_interpreter"] else
         "The clinic does not list a dedicated on-site interpreter. In-app chat translation can be used for "
         "messages, but consider bringing a companion or arranging an interpreter for the consultation."),
        "",
        "## What procedures are offered, and from what price?",
        "",
        "| Procedure | Starting price (KRW) | VAT |",
        "| --- | --- | --- |",
    ]
    by_code = {}
    for o in options:
        by_code.setdefault(o["procedure_code"], []).append(o)
    for code in [p[0] for p in PROCEDURES]:
        if code in by_code:
            cheapest = min(by_code[code], key=lambda o: o["price_krw"])
            lines.append("| %s | %s (%s, %s) | %s |" % (
                PROC_NAME[code]["en"], "{:,}".format(cheapest["price_krw"]), cheapest["product"], cheapest["dose"],
                "included" if cheapest["vat_included"] else "not included"))
    lines += [
        "",
        "Listed prices are reference prices and may differ after an in-person consultation.",
        "",
        "## Who are the doctors?",
        "",
    ]
    for d in docs:
        spec = ", ".join(PROC_NAME[c]["en"] for c in d["specialties"])
        lines.append("- %s (%s), %s — %d years of experience; languages: %s; focus: %s." % (
            d["name_en"], d["name_ko"], d["title"], d["career_years"],
            ", ".join(LANG_NAME_EN[l] for l in d["languages"]), spec))
    lines += [
        "",
        "## How does booking work?",
        "",
        "All reservations require clinic approval. When you request a time, the slot is held for 30 minutes "
        "while the clinic reviews the request. The clinic may confirm it, or decline it and suggest alternative "
        "times. If no decision is made within 30 minutes, the hold is released.",
        "",
        "## Can I cancel or change my reservation?",
        "",
        "You can cancel from the app. Deposit and refund rules, if any, are set by each clinic; ask the clinic "
        "for its cancellation policy before confirming.",
        "",
        "## When was this information last verified?",
        "",
        ("Clinic information was last verified on %s." % h["verified_at"]) if h["verified_at"]
        else "This clinic's information has not been verified yet.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-date", default=dt.datetime.now(KST).date().isoformat())
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--rag-out", default=os.path.join(HERE, "rag_docs", "hospitals"))
    args = ap.parse_args()

    base = dt.date.fromisoformat(args.base_date)
    rng = random.Random(args.seed)

    procedures = gen_procedures()
    hospitals = gen_hospitals(rng, base)
    persona_ids = set()
    for h in hospitals:
        if (h["area_code"] in ("GANGNAM", "MYEONGDONG") and h["category"] != "DERMA"
                and (h["id"] == 1 or len([x for x in persona_ids if x != 1]) < 4)):
            persona_ids.add(h["id"])
            if "zh" not in h["supported_languages"]:
                h["supported_languages"] = [l for l in LANGS if l in h["supported_languages"] + ["zh"]]
            h["has_interpreter"] = True
    offered = {h["id"]: pick_procedures(rng, h, h["id"] in persona_ids) for h in hospitals}
    price_options = gen_price_options(rng, hospitals, offered, base)
    doctors = gen_doctors(rng, hospitals, offered)
    slots = gen_slots(rng, hospitals, doctors, base, persona_ids)
    users = gen_users(rng, base)
    reservations = gen_reservations(rng, base, users, hospitals, slots, offered)
    reviews = gen_reviews(rng, base, hospitals, offered)
    glossary = gen_glossary()
    conversations, consultations, chat_messages = gen_consultations(rng, base, users, price_options, slots)

    data = {
        "hospitals": hospitals, "users": users, "procedures": procedures, "doctors": doctors,
        "price_options": price_options, "slots": slots, "reviews": reviews, "glossary": glossary,
        "conversations": conversations, "consultations": consultations, "chat_messages": chat_messages,
        "reservations": reservations,
    }
    for t in EMPTY_TABLES:
        data[t] = []

    os.makedirs(args.out, exist_ok=True)
    for table, rows in data.items():
        with open(os.path.join(args.out, table + ".json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
            f.write("\n")
    with open(os.path.join(args.out, "schema.sql"), "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)
    with open(os.path.join(args.out, "V100__seed.sql"), "w", encoding="utf-8") as f:
        f.write(build_seed_sql(data, base, args.seed))
    meta = {"base_date": base.isoformat(), "seed": args.seed, "persona_hospital_ids": sorted(persona_ids),
            "counts": {t: len(r) for t, r in data.items()}}
    with open(os.path.join(args.out, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
        f.write("\n")

    os.makedirs(args.rag_out, exist_ok=True)
    docs_by_h, opts_by_h = {}, {}
    for d in doctors:
        docs_by_h.setdefault(d["hospital_id"], []).append(d)
    for o in price_options:
        opts_by_h.setdefault(o["hospital_id"], []).append(o)
    for h in hospitals:
        with open(os.path.join(args.rag_out, "HOSPITAL_FAQ_%03d.md" % h["id"]), "w", encoding="utf-8") as f:
            f.write(hospital_faq(h, docs_by_h[h["id"]], opts_by_h[h["id"]]))

    for t in INSERT_ORDER + EMPTY_TABLES:
        print("%-15s %6d" % (t, len(data[t])))
    print("persona hospitals:", sorted(persona_ids))
    print("wrote", args.out, "and", args.rag_out)


if __name__ == "__main__":
    main()
