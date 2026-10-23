package com.skala.capstone.catalog;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.common.messaging.MessagePublisher;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.web.RequestLocale;

/**
 * 리뷰 번역 (translator 서비스에 위임, backend 는 LLM 을 부르지 않는다).
 *
 * <pre>
 *   리뷰 저장 ──review.translate──▶ translator (원문 언어 감지 + 나머지 3개 언어 번역)
 *   app.review_translations ◀──review.translated──┘
 * </pre>
 *
 * 번역이 오기 전·실패 시에는 원문만 보인다. seed 리뷰 번역은 data/mock/seed_extras.py 가 미리 넣는다.
 * 병원 답글(V106)도 같은 큐로 보낸다: kind = REPLY → app.review_reply_translations (reviewId = 답글이 달린 리뷰).
 * 병원 소개(병원 관리자 수정)도 같다: kind = HOSPITAL → app.hospitals.description_* (reviewId = 병원 id).
 */
@Component
public class ReviewTranslations {

	private static final Logger log = LoggerFactory.getLogger(ReviewTranslations.class);
	private static final List<String> LANGS = List.of("ko", "en", "zh", "ja");

	public static final String KIND_REVIEW = "REVIEW";
	public static final String KIND_REPLY = "REPLY";
	public static final String KIND_HOSPITAL = "HOSPITAL";

	/** backend → translator. from 은 작성자 화면 언어(참고용), translator 가 실제 언어를 감지한다. kind 는 그대로 돌려받는다 */
	public record ReviewTranslate(long reviewId, String text, String from, List<String> to, String kind) {
	}

	/** translator → backend. translations: 감지한 원문 언어를 뺀 언어별 번역문 */
	public record ReviewTranslated(Long reviewId, boolean ok, String detectedLang, Map<String, String> translations,
			String error, String kind) {
	}

	private final JdbcClient jdbc;
	private final MessagePublisher publisher;

	public ReviewTranslations(JdbcClient jdbc, MessagePublisher publisher) {
		this.jdbc = jdbc;
		this.publisher = publisher;
	}

	/** 리뷰 저장 트랜잭션이 커밋된 뒤 번역 요청 (발행 실패는 원문만 보일 뿐이라 로그만 남긴다) */
	public void requestAfterCommit(long reviewId, String text, String from) {
		publisher.publishAfterCommit(Queues.REVIEW_TRANSLATE, new ReviewTranslate(reviewId, text, from, LANGS, KIND_REVIEW),
				() -> log.warn("review translation request not sent for review {}", reviewId));
	}

	/** 병원 답글 저장 후 번역 요청 */
	public void requestReplyAfterCommit(long reviewId, String text, String from) {
		publisher.publishAfterCommit(Queues.REVIEW_TRANSLATE, new ReviewTranslate(reviewId, text, from, LANGS, KIND_REPLY),
				() -> log.warn("reply translation request not sent for review {}", reviewId));
	}

	/** 병원 소개(한국어) 수정 후 다른 언어 번역 요청 */
	public void requestHospitalAfterCommit(long hospitalId, String text, String from) {
		publisher.publishAfterCommit(Queues.REVIEW_TRANSLATE,
				new ReviewTranslate(hospitalId, text, from, LANGS, KIND_HOSPITAL),
				() -> log.warn("hospital description translation request not sent for hospital {}", hospitalId));
	}

	@Transactional
	@RabbitListener(queues = Queues.REVIEW_TRANSLATED)
	public void onTranslated(ReviewTranslated msg) {
		if (msg == null || msg.reviewId() == null) {
			return;
		}
		if (!msg.ok() || msg.translations() == null) {
			log.warn("review {} ({}) translation failed: {}", msg.reviewId(), msg.kind(), msg.error());
			return;
		}
		if (KIND_REPLY.equals(msg.kind())) {
			storeReply(msg);
			return;
		}
		if (KIND_HOSPITAL.equals(msg.kind())) {
			storeHospital(msg);
			return;
		}
		String source = RequestLocale.SUPPORTED.contains(msg.detectedLang()) ? msg.detectedLang() : null;
		if (source != null) {
			// 화면 언어와 실제 글 언어가 다르면 원문 언어를 바로잡고, 원문 언어의 번역 행은 지운다
			jdbc.sql("UPDATE app.reviews SET lang = :lang WHERE id = :id").param("lang", source)
					.param("id", msg.reviewId()).update();
			jdbc.sql("DELETE FROM app.review_translations WHERE review_id = :id AND lang = :lang")
					.param("id", msg.reviewId()).param("lang", source).update();
		}
		msg.translations().forEach((lang, text) -> {
			if (!LANGS.contains(lang) || lang.equals(source) || text == null || text.isBlank()) {
				return;
			}
			jdbc.sql("""
					INSERT INTO app.review_translations (review_id, lang, content) VALUES (:id, :lang, :content)
					ON CONFLICT (review_id, lang) DO UPDATE SET content = EXCLUDED.content
					""").param("id", msg.reviewId()).param("lang", lang).param("content", text.trim()).update();
		});
	}

	/** 답글 번역 저장. 그 사이 답글이 지워졌으면(FK 없음) 버린다 */
	private void storeReply(ReviewTranslated msg) {
		String source = RequestLocale.SUPPORTED.contains(msg.detectedLang()) ? msg.detectedLang() : null;
		if (source != null) {
			jdbc.sql("UPDATE app.review_replies SET lang = :lang WHERE review_id = :id").param("lang", source)
					.param("id", msg.reviewId()).update();
		}
		msg.translations().forEach((lang, text) -> {
			if (!LANGS.contains(lang) || lang.equals(source) || text == null || text.isBlank()) {
				return;
			}
			jdbc.sql("""
					INSERT INTO app.review_reply_translations (review_id, lang, content)
					SELECT review_id, :lang, :content FROM app.review_replies WHERE review_id = :id
					ON CONFLICT (review_id, lang) DO UPDATE SET content = EXCLUDED.content
					""").param("id", msg.reviewId()).param("lang", lang).param("content", text.trim()).update();
		});
	}

	/** 병원 소개 번역 저장. 컬럼 이름은 고정 목록(LANGS)에서만 고른다 */
	private void storeHospital(ReviewTranslated msg) {
		msg.translations().forEach((lang, text) -> {
			if (!LANGS.contains(lang) || lang.equals(msg.detectedLang()) || text == null || text.isBlank()) {
				return;
			}
			jdbc.sql("UPDATE app.hospitals SET description_" + lang + " = :text WHERE id = :id")
					.param("text", text.trim()).param("id", msg.reviewId()).update();
		});
	}

	@RabbitListener(queues = Queues.REVIEW_TRANSLATE_DLQ)
	public void onDeadLetter(JsonNode body) {
		log.warn("review translation gave up (shown in original language): {}", body);
	}
}
