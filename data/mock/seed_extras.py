"""Seed additions kept out of generate.py so the original generators stay untouched (stdlib only).

1) Review translations: every seed review is composed from REVIEW templates in generate.py. Each template
   sentence below carries its translations, so a review is split back into its sentences and re-joined
   in the other three languages. No LLM call, deterministic, and the original review rows do not change.
2) Slot extension: generate.py makes 21 days of slots. Days 21..SLOT_DAYS-1 are appended AFTER every other
   generator has run, with a separate RNG, so existing slot ids and all other tables stay identical.
"""
import datetime as dt
import random

LANGS = ["ko", "en", "zh", "ja"]
JOIN = {"ko": " ", "en": " ", "zh": "", "ja": ""}

# base-date 2026-10-22 + 39 days = 2026-11-30 (last bookable day)
SLOT_DAYS = 40
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_KST = dt.timezone(dt.timedelta(hours=9))

# One entry per template sentence in generate.REVIEW. The source language holds the exact template text.
# {area} / {proc} are filled with the target-language area and procedure names.
SENTENCES = [
    # ---- ko
    {"ko": "{area}에서 {proc} 받았어요.", "en": "I got {proc} in {area}.", "zh": "在{area}做了{proc}。", "ja": "{area}で{proc}を受けました。"},
    {"ko": "{proc} 상담부터 시술까지 이곳에서 했습니다.", "en": "I had everything from the {proc} consultation to the treatment here.", "zh": "从{proc}咨询到治疗都是在这里做的。", "ja": "{proc}のカウンセリングから施術までこちらで受けました。"},
    {"ko": "지인 추천으로 방문해서 {proc} 했어요.", "en": "I came on a friend's recommendation and got {proc}.", "zh": "经朋友推荐来这里做了{proc}。", "ja": "知人の紹介で来院して{proc}を受けました。"},
    {"ko": "결과가 자연스럽고 만족스러워요.", "en": "The result is natural and I'm satisfied.", "zh": "效果自然，很满意。", "ja": "仕上がりが自然で満足しています。"},
    {"ko": "생각보다 통증이 적었고 붓기도 금방 빠졌어요.", "en": "There was less pain than I thought, and the swelling went down quickly.", "zh": "比想象中疼痛少，消肿也很快。", "ja": "思ったより痛みが少なく、腫れもすぐに引きました。"},
    {"ko": "원장님이 원하는 스타일을 꼼꼼하게 물어봐 주셨어요.", "en": "The doctor carefully asked about the style I wanted.", "zh": "院长仔细询问了我想要的风格。", "ja": "院長が希望のスタイルを丁寧に聞いてくれました。"},
    {"ko": "상담실장님이 친절하게 설명해 주셨어요.", "en": "The consultation manager explained things kindly.", "zh": "咨询室长很亲切地做了说明。", "ja": "カウンセラーの方が親切に説明してくれました。"},
    {"ko": "대기 시간이 짧아서 좋았어요.", "en": "The short waiting time was nice.", "zh": "等待时间短，很好。", "ja": "待ち時間が短くてよかったです。"},
    {"ko": "사후 관리 안내가 자세했어요.", "en": "The aftercare guidance was detailed.", "zh": "术后护理说明很详细。", "ja": "アフターケアの案内が詳しかったです。"},
    {"ko": "다음에도 재방문 의사 있어요.", "en": "I'd come back again.", "zh": "下次还愿意再来。", "ja": "また来たいと思います。"},
    {"ko": "주변에도 추천하고 싶어요.", "en": "I'd like to recommend it to people around me.", "zh": "也想推荐给身边的人。", "ja": "周りの人にもすすめたいです。"},
    {"ko": "결과는 무난한 편이에요.", "en": "The result is fairly okay.", "zh": "效果还算可以。", "ja": "仕上がりはまずまずです。"},
    {"ko": "효과가 기대만큼 크진 않았지만 나쁘지 않아요.", "en": "The effect wasn't as big as I expected, but it's not bad.", "zh": "效果没有期待的那么明显，但也不差。", "ja": "効果は期待ほど大きくなかったですが、悪くないです。"},
    {"ko": "대기 시간이 조금 길었어요.", "en": "The waiting time was a little long.", "zh": "等待时间有点长。", "ja": "待ち時間が少し長かったです。"},
    {"ko": "상담은 무난했어요.", "en": "The consultation was fine.", "zh": "咨询还算顺利。", "ja": "カウンセリングは問題ありませんでした。"},
    {"ko": "가격 대비 괜찮은 편입니다.", "en": "It's decent for the price.", "zh": "性价比还不错。", "ja": "価格の割には悪くないです。"},
    {"ko": "한 번 더 받아보고 판단하려고요.", "en": "I'll try it once more before deciding.", "zh": "打算再做一次再判断。", "ja": "もう一度受けてから判断しようと思います。"},
    {"ko": "기대했던 결과와 달라서 아쉬워요.", "en": "It's disappointing that the result was different from what I expected.", "zh": "效果和期待的不一样，有点遗憾。", "ja": "期待していた仕上がりと違って残念です。"},
    {"ko": "붓기가 생각보다 오래갔어요.", "en": "The swelling lasted longer than I thought.", "zh": "肿胀持续得比想象中久。", "ja": "腫れが思ったより長引きました。"},
    {"ko": "상담이 조금 급하게 진행된 느낌이었어요.", "en": "The consultation felt a bit rushed.", "zh": "感觉咨询进行得有点匆忙。", "ja": "カウンセリングが少し急いで進められた感じでした。"},
    {"ko": "예약 시간보다 많이 기다렸어요.", "en": "I waited a long time past my appointment.", "zh": "比预约时间等了很久。", "ja": "予約時間よりかなり待ちました。"},
    {"ko": "재방문은 고민 중입니다.", "en": "I'm still thinking about whether to come back.", "zh": "还在考虑要不要再来。", "ja": "再訪するかは迷っています。"},
    {"ko": "다른 곳과 비교해 보고 결정하세요.", "en": "Compare with other places before deciding.", "zh": "建议和其他地方比较后再决定。", "ja": "他のところと比べてから決めてください。"},
    # ---- en
    {"en": "Got {proc} here while visiting {area}.", "ko": "{area} 방문 중에 여기서 {proc} 받았어요.", "zh": "来{area}的时候在这里做了{proc}。", "ja": "{area}を訪れた際にこちらで{proc}を受けました。"},
    {"en": "I did my {proc} consultation and treatment at this clinic.", "ko": "이 병원에서 {proc} 상담과 시술을 받았어요.", "zh": "我在这家诊所做了{proc}的咨询和治疗。", "ja": "このクリニックで{proc}のカウンセリングと施術を受けました。"},
    {"en": "A friend recommended this place for {proc}.", "ko": "친구가 {proc} 하려면 여기를 추천해 줬어요.", "zh": "朋友推荐我来这里做{proc}。", "ja": "友人に{proc}ならここだとすすめられました。"},
    {"en": "The result looks natural and I'm very happy with it.", "ko": "결과가 자연스러워 보여서 아주 만족해요.", "zh": "效果看起来很自然，我非常满意。", "ja": "仕上がりが自然で、とても満足しています。"},
    {"en": "Less pain than I expected, and the swelling went down quickly.", "ko": "예상보다 덜 아팠고 붓기도 빨리 빠졌어요.", "zh": "比预想的疼痛少，消肿也很快。", "ja": "予想より痛みが少なく、腫れもすぐに引きました。"},
    {"en": "The doctor took time to understand the look I wanted.", "ko": "의사 선생님이 제가 원하는 모습을 시간을 들여 이해해 주셨어요.", "zh": "医生花时间了解了我想要的效果。", "ja": "先生が時間をかけて希望の雰囲気を理解してくれました。"},
    {"en": "The interpreter was very helpful.", "ko": "통역사분이 정말 큰 도움이 됐어요.", "zh": "翻译人员帮了很大的忙。", "ja": "通訳の方がとても助けになりました。"},
    {"en": "Staff explained everything clearly in English.", "ko": "직원들이 모든 걸 영어로 명확하게 설명해 줬어요.", "zh": "工作人员用英语把一切都解释得很清楚。", "ja": "スタッフが英語ですべてわかりやすく説明してくれました。"},
    {"en": "Aftercare instructions were detailed.", "ko": "사후 관리 안내가 자세했어요.", "zh": "术后护理说明很详细。", "ja": "アフターケアの説明が詳しかったです。"},
    {"en": "Would definitely come back.", "ko": "꼭 다시 오고 싶어요.", "zh": "一定还会再来。", "ja": "ぜひまた来たいです。"},
    {"en": "I'd recommend it to friends visiting Seoul.", "ko": "서울에 오는 친구들에게 추천하고 싶어요.", "zh": "会推荐给来首尔的朋友。", "ja": "ソウルに来る友人にすすめたいです。"},
    {"en": "The result is okay, nothing dramatic.", "ko": "결과는 괜찮지만 큰 변화는 없어요.", "zh": "效果还可以，没有太大变化。", "ja": "仕上がりはまずまずで、大きな変化はありません。"},
    {"en": "Effect was a bit less than I hoped, but fine.", "ko": "효과가 기대보다 조금 덜했지만 괜찮아요.", "zh": "效果比期望的稍差一些，但还可以。", "ja": "効果は期待より少し控えめでしたが、問題ありません。"},
    {"en": "Waiting time was a little long.", "ko": "대기 시간이 조금 길었어요.", "zh": "等待时间有点长。", "ja": "待ち時間が少し長かったです。"},
    {"en": "Communication was okay with some translation gaps.", "ko": "소통은 괜찮았지만 통역이 매끄럽지 않은 부분이 있었어요.", "zh": "沟通还可以，但翻译上有些不到位。", "ja": "コミュニケーションは問題ありませんでしたが、通訳に少し抜けがありました。"},
    {"en": "Reasonable for the price.", "ko": "가격 대비 괜찮아요.", "zh": "以这个价格来说还算合理。", "ja": "価格相応だと思います。"},
    {"en": "Might try once more before deciding.", "ko": "한 번 더 받아보고 결정할까 해요.", "zh": "可能会再做一次再决定。", "ja": "もう一度受けてから決めるかもしれません。"},
    {"en": "The result was not what I expected.", "ko": "결과가 기대했던 것과 달랐어요.", "zh": "效果和我预期的不一样。", "ja": "仕上がりが期待していたものと違いました。"},
    {"en": "Swelling lasted longer than I was told.", "ko": "붓기가 안내받은 것보다 오래갔어요.", "zh": "肿胀持续的时间比告知的要长。", "ja": "腫れが説明されたより長く続きました。"},
    {"en": "The consultation felt rushed.", "ko": "상담이 급하게 진행된 느낌이었어요.", "zh": "咨询感觉很匆忙。", "ja": "カウンセリングが慌ただしく感じました。"},
    {"en": "I waited a long time past my appointment.", "ko": "예약 시간보다 한참 기다렸어요.", "zh": "过了预约时间还等了很久。", "ja": "予約時間を過ぎてから長く待ちました。"},
    {"en": "Not sure I would return.", "ko": "다시 올지는 잘 모르겠어요.", "zh": "不确定会不会再来。", "ja": "また来るかはわかりません。"},
    {"en": "Compare a few clinics before booking.", "ko": "예약 전에 몇 군데 비교해 보세요.", "zh": "预约前建议比较几家诊所。", "ja": "予約する前にいくつかのクリニックを比べてみてください。"},
    # ---- zh
    {"zh": "在{area}做了{proc}。", "ko": "{area}에서 {proc} 받았어요.", "en": "I got {proc} in {area}.", "ja": "{area}で{proc}を受けました。"},
    {"zh": "从咨询到{proc}都是在这家做的。", "ko": "상담부터 {proc}까지 모두 이곳에서 했어요.", "en": "I had everything from the consultation to {proc} at this clinic.", "ja": "カウンセリングから{proc}まで、すべてこちらで受けました。"},
    {"zh": "朋友推荐来做{proc}。", "ko": "친구 추천으로 {proc} 하러 왔어요.", "en": "A friend recommended I come here for {proc}.", "ja": "友人の紹介で{proc}を受けに来ました。"},
    {"zh": "效果很自然，非常满意。", "ko": "결과가 아주 자연스러워서 매우 만족해요.", "en": "The result is very natural and I'm very satisfied.", "ja": "仕上がりがとても自然で、大満足です。"},
    {"zh": "比想象中不疼，消肿也很快。", "ko": "생각보다 아프지 않았고 붓기도 빨리 빠졌어요.", "en": "It hurt less than I imagined, and the swelling went down quickly.", "ja": "想像より痛くなく、腫れもすぐに引きました。"},
    {"zh": "院长很仔细地询问了我想要的风格。", "ko": "원장님이 제가 원하는 스타일을 아주 꼼꼼하게 물어봐 주셨어요.", "en": "The doctor asked very carefully about the style I wanted.", "ja": "院長が希望のスタイルをとても丁寧に聞いてくれました。"},
    {"zh": "翻译人员很专业，沟通没有问题。", "ko": "통역사분이 전문적이어서 소통에 문제가 없었어요.", "en": "The interpreter was professional, and communication was no problem.", "ja": "通訳の方がプロで、コミュニケーションに問題はありませんでした。"},
    {"zh": "咨询师讲解得很耐心。", "ko": "상담사분이 인내심 있게 설명해 주셨어요.", "en": "The counselor explained things patiently.", "ja": "カウンセラーの方が根気よく説明してくれました。"},
    {"zh": "术后护理说明很详细。", "ko": "사후 관리 안내가 자세했어요.", "en": "The aftercare instructions were detailed.", "ja": "アフターケアの説明が詳しかったです。"},
    {"zh": "下次还会再来。", "ko": "다음에 또 올 거예요.", "en": "I'll come again next time.", "ja": "次回もまた来ます。"},
    {"zh": "推荐给来首尔的朋友。", "ko": "서울에 오는 친구들에게 추천해요.", "en": "I recommend it to friends coming to Seoul.", "ja": "ソウルに来る友人におすすめします。"},
    {"zh": "效果还可以，比较普通。", "ko": "결과는 괜찮은 편이고 평범해요.", "en": "The result is okay, fairly ordinary.", "ja": "仕上がりはまあまあで、普通です。"},
    {"zh": "效果没有预期那么明显，但还不错。", "ko": "효과가 기대만큼 뚜렷하진 않았지만 괜찮아요.", "en": "The effect wasn't as noticeable as I expected, but it's not bad.", "ja": "効果は期待ほどはっきりしませんでしたが、悪くないです。"},
    {"zh": "等待时间有点长。", "ko": "대기 시간이 조금 길었어요.", "en": "The waiting time was a bit long.", "ja": "待ち時間が少し長かったです。"},
    {"zh": "沟通基本顺利。", "ko": "소통은 대체로 원활했어요.", "en": "Communication went mostly smoothly.", "ja": "コミュニケーションはおおむねスムーズでした。"},
    {"zh": "性价比还可以。", "ko": "가성비는 괜찮은 편이에요.", "en": "Value for money is okay.", "ja": "コスパはまあまあです。"},
    {"zh": "打算再做一次看看。", "ko": "한 번 더 받아보려고 해요.", "en": "I plan to try it once more and see.", "ja": "もう一度受けてみるつもりです。"},
    {"zh": "效果和预期不太一样，有点失望。", "ko": "결과가 기대와 좀 달라서 조금 실망했어요.", "en": "The result was a bit different from what I expected; a little disappointing.", "ja": "仕上がりが期待と少し違い、ちょっとがっかりしました。"},
    {"zh": "肿胀持续时间比说的要长。", "ko": "붓기가 안내받은 것보다 오래갔어요.", "en": "The swelling lasted longer than I was told.", "ja": "腫れが説明より長く続きました。"},
    {"zh": "咨询感觉有点匆忙。", "ko": "상담이 조금 급하게 느껴졌어요.", "en": "The consultation felt a bit rushed.", "ja": "カウンセリングが少し慌ただしく感じました。"},
    {"zh": "比预约时间等了很久。", "ko": "예약 시간보다 한참 기다렸어요.", "en": "I waited a long time past my appointment.", "ja": "予約時間よりかなり待ちました。"},
    {"zh": "不太确定会不会再来。", "ko": "다시 올지는 잘 모르겠어요.", "en": "I'm not sure whether I'll come back.", "ja": "また来るかはよくわかりません。"},
    {"zh": "建议多比较几家再决定。", "ko": "여러 곳을 비교해 보고 결정하는 걸 추천해요.", "en": "I suggest comparing a few places before deciding.", "ja": "何か所か比べてから決めることをおすすめします。"},
    # ---- ja
    {"ja": "{area}で{proc}を受けました。", "ko": "{area}에서 {proc} 받았어요.", "en": "I got {proc} in {area}.", "zh": "在{area}做了{proc}。"},
    {"ja": "{proc}のカウンセリングから施術までこちらでお願いしました。", "ko": "{proc} 상담부터 시술까지 이곳에 맡겼어요.", "en": "I had this clinic handle everything from the {proc} consultation to the treatment.", "zh": "{proc}从咨询到治疗都交给了这家。"},
    {"ja": "友人の紹介で{proc}を受けに来ました。", "ko": "친구 소개로 {proc} 받으러 왔어요.", "en": "I came for {proc} on a friend's referral.", "zh": "经朋友介绍来做{proc}。"},
    {"ja": "仕上がりが自然でとても満足しています。", "ko": "결과가 자연스러워서 아주 만족해요.", "en": "The result is natural and I'm very satisfied.", "zh": "效果自然，非常满意。"},
    {"ja": "思ったより痛みが少なく、腫れもすぐ引きました。", "ko": "생각보다 통증이 적었고 붓기도 금방 빠졌어요.", "en": "There was less pain than I thought, and the swelling went down quickly.", "zh": "比想象中疼痛少，消肿也很快。"},
    {"ja": "先生が希望のデザインを丁寧に聞いてくれました。", "ko": "선생님이 원하는 디자인을 꼼꼼하게 들어 주셨어요.", "en": "The doctor listened carefully to the design I wanted.", "zh": "医生很仔细地听取了我想要的设计。"},
    {"ja": "通訳の方がいて安心できました。", "ko": "통역사분이 계셔서 안심이 됐어요.", "en": "Having an interpreter there put me at ease.", "zh": "有翻译人员在，很安心。"},
    {"ja": "スタッフの説明がわかりやすかったです。", "ko": "직원분들의 설명이 이해하기 쉬웠어요.", "en": "The staff's explanations were easy to understand.", "zh": "工作人员的说明很容易理解。"},
    {"ja": "アフターケアの案内が丁寧でした。", "ko": "사후 관리 안내가 꼼꼼했어요.", "en": "The aftercare guidance was thorough.", "zh": "术后护理的说明很细致。"},
    {"ja": "また利用したいです。", "ko": "또 이용하고 싶어요.", "en": "I'd like to use this clinic again.", "zh": "还想再来。"},
    {"ja": "友人にもすすめたいです。", "ko": "친구에게도 추천하고 싶어요.", "en": "I'd like to recommend it to friends too.", "zh": "也想推荐给朋友。"},
    {"ja": "仕上がりは普通だと思います。", "ko": "결과는 평범한 편인 것 같아요.", "en": "I think the result is average.", "zh": "我觉得效果比较普通。"},
    {"ja": "期待ほどではないですが悪くないです。", "ko": "기대만큼은 아니지만 나쁘지 않아요.", "en": "Not as good as I hoped, but not bad.", "zh": "虽然没有期待的那么好，但也不差。"},
    {"ja": "待ち時間が少し長かったです。", "ko": "대기 시간이 조금 길었어요.", "en": "The waiting time was a little long.", "zh": "等待时间有点长。"},
    {"ja": "説明は一通りしてもらえました。", "ko": "설명은 기본적인 건 다 들었어요.", "en": "They covered the basics in their explanation.", "zh": "基本的说明都有。"},
    {"ja": "価格相応だと思います。", "ko": "가격만큼은 하는 것 같아요.", "en": "I think it's worth the price.", "zh": "我觉得物有所值。"},
    {"ja": "もう一度受けてから判断します。", "ko": "한 번 더 받아보고 판단할게요.", "en": "I'll decide after trying it once more.", "zh": "再做一次后再判断。"},
    {"ja": "思っていた仕上がりと違って残念です。", "ko": "생각했던 결과와 달라서 아쉬워요.", "en": "It's a shame the result differed from what I had in mind.", "zh": "效果和我想的不一样，很遗憾。"},
    {"ja": "腫れが説明より長く続きました。", "ko": "붓기가 안내받은 것보다 오래갔어요.", "en": "The swelling lasted longer than explained.", "zh": "肿胀持续的时间比说明的要长。"},
    {"ja": "カウンセリングが少し急ぎ足でした。", "ko": "상담이 조금 서두르는 느낌이었어요.", "en": "The consultation was a little hurried.", "zh": "咨询有点仓促。"},
    {"ja": "予約時間よりかなり待ちました。", "ko": "예약 시간보다 꽤 기다렸어요.", "en": "I waited quite a while past my appointment time.", "zh": "比预约时间等了挺久。"},
    {"ja": "再訪は迷っています。", "ko": "재방문은 고민하고 있어요.", "en": "I'm undecided about coming back.", "zh": "还在犹豫要不要再来。"},
    {"ja": "いくつか比較してから決めるのがおすすめです。", "ko": "몇 군데 비교해 보고 결정하는 걸 추천해요.", "en": "I recommend comparing a few places before deciding.", "zh": "建议比较几家后再决定。"},
]

REVIEW_TRANSLATIONS_SQL = """
-- Review translations (seed: from templates in data/mock/seed_extras.py; new reviews: translator service).
-- The original text stays in app.reviews (lang = source language); one row per other language.
CREATE TABLE app.review_translations (
    id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    review_id  bigint NOT NULL REFERENCES app.reviews(id) ON DELETE CASCADE,
    lang       varchar(5) NOT NULL CHECK (lang IN ('ko','en','zh','ja')),
    content    text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (review_id, lang)
);
"""

REVIEW_TRANSLATIONS_COLUMNS = {"id": "int", "review_id": "int", "lang": "text", "content": "text",
                               "created_at": "text"}


def _split(content, candidates):
    """Split a composed review back into template sentences (longest match first at each position)."""
    parts, pos = [], 0
    while pos < len(content):
        if content[pos] == " ":
            pos += 1
            continue
        hit = max((c for c in candidates if content.startswith(c, pos)), key=len, default=None)
        if hit is None:
            raise ValueError("unknown review sentence at %r" % content[pos:pos + 40])
        parts.append(hit)
        pos += len(hit)
    return parts


def gen_review_translations(reviews, hospitals, area_names, proc_names):
    """One row per (review, language other than the source). area_names: area_code -> {lang: name}."""
    area_of = {h["id"]: area_names[h["area_code"]] for h in hospitals}
    rows = []
    for r in reviews:
        src = r["lang"]
        area, proc = area_of[r["hospital_id"]], proc_names[r["procedure_code"]]
        formatted = {}
        for e in SENTENCES:
            if src in e:
                formatted.setdefault(e[src].format(area=area[src], proc=proc[src]), e)
        parts = _split(r["content"], formatted)
        for lang in LANGS:
            if lang == src:
                continue
            text = JOIN[lang].join(formatted[p][lang].format(area=area[lang], proc=proc[lang]) for p in parts)
            rows.append({"id": len(rows) + 1, "review_id": r["id"], "lang": lang, "content": text,
                         "created_at": r["created_at"]})
    return rows


def extend_slots(slots, hospitals, base, seed, days=SLOT_DAYS):
    """Append slots for days 21..days-1 after the existing ones (same hours rule as generate.gen_slots).

    Separate RNG so the main generator's random stream (and every other table) is unchanged.
    Booked ratio per hospital follows that hospital's existing slots; doctors keep rotating in order.
    """
    rng = random.Random("%d-slot-extension" % seed)
    by_h = {}
    for s in slots:
        by_h.setdefault(s["hospital_id"], []).append(s)
    first_day = 1 + max((dt.datetime.fromisoformat(s["start_at"]).date() - base).days for s in slots)
    next_id = max(s["id"] for s in slots) + 1
    for h in hospitals:
        own = by_h.get(h["id"], [])
        if not own:
            continue
        booked_rate = sum(1 for s in own if s["status"] == "BOOKED") / float(len(own))
        # doctor rotation as in gen_slots: doctor ids in first-appearance order, k continues
        docs = list(dict.fromkeys(s["doctor_id"] for s in own))
        k = len(own)
        for day in range(first_day, days):
            d = base + dt.timedelta(days=day)
            hours = h["open_hours"][_DAYS[d.weekday()]]
            if not hours:
                continue
            start = max(_hhmm(hours["open"]), 10 * 60)
            end = min(_hhmm(hours["close"]), 18 * 60)
            t = (start + 29) // 30 * 30
            while t + 30 <= end:
                s = dt.datetime(d.year, d.month, d.day, t // 60, t % 60, tzinfo=_KST)
                slots.append({
                    "id": next_id, "hospital_id": h["id"], "doctor_id": docs[k % len(docs)],
                    "start_at": s.isoformat(), "end_at": (s + dt.timedelta(minutes=30)).isoformat(),
                    "status": "BOOKED" if rng.random() < booked_rate else "AVAILABLE",
                    "hold_expires_at": None, "version": 0,
                })
                next_id += 1
                k += 1
                t += 30
    return slots


def _hhmm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def validate_review_translations(d, check):
    """Every review has exactly the three other languages, none equal to the source language."""
    reviews = {r["id"]: r for r in d["reviews"]}
    seen = set()
    for t in d.get("review_translations", []):
        r = reviews.get(t["review_id"])
        check(r is not None, "review_translation %d review FK" % t["id"])
        if r is None:
            continue
        check(t["lang"] in LANGS and t["lang"] != r["lang"], "review_translation %d lang" % t["id"])
        check(bool(t["content"].strip()), "review_translation %d empty" % t["id"])
        check("{" not in t["content"], "review_translation %d unfilled placeholder" % t["id"])
        check((t["review_id"], t["lang"]) not in seen, "review_translation %d duplicate" % t["id"])
        seen.add((t["review_id"], t["lang"]))
    seed_reviews = [r for r in d["reviews"] if r.get("user_id") is None]
    check(len(seen) == 3 * len(seed_reviews), "review_translations: %d rows for %d seed reviews"
          % (len(seen), len(seed_reviews)))
