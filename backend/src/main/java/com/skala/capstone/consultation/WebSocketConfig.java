package com.skala.capstone.consultation;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

import com.skala.capstone.common.config.AppProperties;

/**
 * STOMP over WebSocket (07 문서 4장). 엔드포인트 /ws (SockJS 없음, FE 는 @stomp/stompjs).
 * - 보내기: /app/consultations/{id}/send
 * - 받기: /topic/consultations/{id} (상담방), /user/queue/notifications (알림), /user/queue/errors (오류)
 * 브로커는 backend 메모리(simple broker) — 단일 인스턴스 로컬 실행 기준.
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

	private final StompAuthInterceptor authInterceptor;
	private final AppProperties app;

	public WebSocketConfig(StompAuthInterceptor authInterceptor, AppProperties app) {
		this.authInterceptor = authInterceptor;
		this.app = app;
	}

	@Override
	public void registerStompEndpoints(StompEndpointRegistry registry) {
		registry.addEndpoint("/ws").setAllowedOrigins(app.cors().allowedOrigins().toArray(String[]::new));
	}

	@Override
	public void configureMessageBroker(MessageBrokerRegistry registry) {
		registry.setApplicationDestinationPrefixes("/app");
		registry.enableSimpleBroker("/topic", "/queue");
		registry.setUserDestinationPrefix("/user");
	}

	@Override
	public void configureClientInboundChannel(ChannelRegistration registration) {
		registration.interceptors(authInterceptor);
	}
}
