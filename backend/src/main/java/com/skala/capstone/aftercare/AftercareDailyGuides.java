package com.skala.capstone.aftercare;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 매일 정해진 시간(기본 오전 9시, Asia/Seoul)에 그날 시술 관리 안내를 보낸다.
 * 시각은 app.aftercare.daily-cron (환경변수 APP_AFTERCARE_DAILY_CRON)으로 바꾼다. 운영자 버튼과 같은 작업이다.
 */
@Component
public class AftercareDailyGuides {

	private static final Logger log = LoggerFactory.getLogger(AftercareDailyGuides.class);

	private final AftercareService aftercare;

	public AftercareDailyGuides(AftercareService aftercare) {
		this.aftercare = aftercare;
	}

	@Scheduled(cron = "${app.aftercare.daily-cron:0 0 9 * * *}", zone = "Asia/Seoul")
	public void run() {
		var result = aftercare.sendDailyGuides();
		log.info("daily aftercare guides: checked {}, requested {}", result.checked(), result.requested());
	}
}
