"""리뷰 번역: 문자 종류로 원문 언어 감지, 원문 언어 제외 3개 언어, 숫자 불일치 언어 제외, 큐가 없어도 기동."""

import json

from aio_pika.exceptions import ChannelNotFoundEntity

from app import review
from app.review import ReviewTranslate, ReviewTranslated, ReviewTranslation, detect_lang, translate_review


def test_detect_lang_by_script():
    assert detect_lang("상담이 친절했어요. Shurink 결과도 좋아요.", "en") == "ko"
    assert detect_lang("仕上がりが自然で満足しています。", "en") == "ja"
    assert detect_lang("效果很自然，非常满意。", "en") == "zh"
    assert detect_lang("The result looks natural.", "ko") == "en"
    assert detect_lang("👍 5/5", "ja") == "ja"          # 글자가 없으면 작성자 화면 언어


def test_messages_are_camel_case():
    msg = ReviewTranslate.model_validate_json('{"reviewId":7,"text":"t","from":"en","to":["ko","en","zh","ja"]}')
    assert msg.review_id == 7 and msg.from_ == "en"
    out = json.loads(ReviewTranslated(review_id=7, ok=True, detected_lang="ko",
                                      translations={"en": "x"}).to_json())
    assert set(out) == {"reviewId", "ok", "detectedLang", "translations", "error"}


async def test_source_language_detected_and_excluded(fake_llm):
    # 화면 언어는 en 이지만 한국어로 쓴 리뷰 → ko 는 번역하지 않는다
    llm = fake_llm(ReviewTranslation(ko="무시", en="The staff were kind.", zh="工作人员很亲切。",
                                     ja="スタッフが親切でした。"))
    out = await translate_review(ReviewTranslate(review_id=1, text="직원분들이 친절했어요.", from_="en"))
    assert out.ok and out.detected_lang == "ko"
    assert set(out.translations) == {"en", "zh", "ja"}
    assert "from Korean into English, Simplified Chinese, Japanese" in llm.calls[0]


async def test_number_mismatch_language_dropped(fake_llm):
    fake_llm(ReviewTranslation(ko="30만 원이었어요", zh="价格是30万韩元。", ja="40万ウォンでした。"))
    out = await translate_review(ReviewTranslate(review_id=2, text="It cost 300000 won, 30만.", from_="en"))
    assert "ja" not in out.translations
    assert set(out.translations) <= {"ko", "zh"}


async def test_glossary_terms_injected_per_target(fake_llm):
    llm = fake_llm(ReviewTranslation(en="Jaw Botox was good.", zh="瘦脸针不错。", ja="エラボトックスがよかったです。"))
    await translate_review(ReviewTranslate(review_id=3, text="사각턱 보톡스 좋았어요.", from_="ko"))
    assert "사각턱 보톡스" in llm.calls[0]


async def test_missing_queue_does_not_block_startup(monkeypatch):
    class Channel:
        is_closed = False

        async def set_qos(self, prefetch_count):
            pass

        async def get_queue(self, name):
            raise ChannelNotFoundEntity()

        async def close(self):
            self.is_closed = True

    class Connection:
        is_closed = True                      # 재시도 루프가 바로 끝나도록

        async def channel(self):
            return Channel()

    scheduled = []
    monkeypatch.setattr(review.asyncio, "create_task", lambda coro: scheduled.append(coro) or coro.close())
    await review.start_review_consumer(Connection())   # 예외 없이 돌아와야 채팅·요약 번역이 계속 뜬다
    assert len(scheduled) == 1
