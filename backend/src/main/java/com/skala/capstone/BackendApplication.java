package com.skala.capstone;

import java.util.TimeZone;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@ConfigurationPropertiesScan
@EnableScheduling // 예약 홀드 만료(1분), 멈춘 AI 작업 정리
public class BackendApplication {

	public static void main(String[] args) {
		// 계약서 1장: 시간대 기준 Asia/Seoul
		TimeZone.setDefault(TimeZone.getTimeZone("Asia/Seoul"));
		SpringApplication.run(BackendApplication.class, args);
	}
}
