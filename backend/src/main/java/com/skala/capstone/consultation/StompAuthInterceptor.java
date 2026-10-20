package com.skala.capstone.consultation;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageDeliveryException;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.stereotype.Component;

import com.skala.capstone.auth.JwtProvider;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;

import io.jsonwebtoken.JwtException;

/**
 * STOMP 인증·인가 (11 문서 4장).
 * - CONNECT: Authorization: Bearer {access} 검증 → 이 연결의 사용자로 고정
 * - SUBSCRIBE /topic/consultations/{id}: 상담 당사자만 (아니면 거부 + 감사 로그)
 * - /user/queue/** 는 Spring 이 자기 큐로만 연결해 준다
 */
@Component
public class StompAuthInterceptor implements ChannelInterceptor {

	private static final Pattern CONSULTATION_TOPIC = Pattern.compile("^/topic/consultations/(\\d+)$");

	private final JwtProvider jwt;
	private final ConsultationAccess access;
	private final AuditLogger audit;

	public StompAuthInterceptor(JwtProvider jwt, ConsultationAccess access, AuditLogger audit) {
		this.jwt = jwt;
		this.access = access;
		this.audit = audit;
	}

	@Override
	public Message<?> preSend(Message<?> message, MessageChannel channel) {
		StompHeaderAccessor accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
		if (accessor == null || accessor.getCommand() == null) {
			return message;
		}
		if (accessor.getCommand() == StompCommand.CONNECT) {
			String header = accessor.getFirstNativeHeader("Authorization");
			if (header == null || !header.startsWith("Bearer ")) {
				throw new MessageDeliveryException("UNAUTHENTICATED");
			}
			try {
				CurrentUser user = jwt.parse(header.substring(7).trim());
				accessor.setUser(new UsernamePasswordAuthenticationToken(user, null, user.authorities()));
			} catch (JwtException | IllegalArgumentException e) {
				throw new MessageDeliveryException("UNAUTHENTICATED");
			}
			return message;
		}
		if (accessor.getCommand() == StompCommand.SUBSCRIBE) {
			CurrentUser user = currentUser(accessor);
			String destination = accessor.getDestination();
			Matcher m = destination == null ? null : CONSULTATION_TOPIC.matcher(destination);
			if (m != null && m.matches()) {
				long id = Long.parseLong(m.group(1));
				boolean allowed = access.find(id).map(p -> access.canAccess(user, p)).orElse(false);
				if (!allowed) {
					audit.log(user, "ACCESS_DENIED", "STOMP SUBSCRIBE " + destination, Map.of());
					throw new MessageDeliveryException("ACCESS_DENIED");
				}
			} else if (destination == null || !(destination.startsWith("/user/queue/"))) {
				// 허용된 구독 주소는 상담방 토픽과 개인 큐뿐
				throw new MessageDeliveryException("ACCESS_DENIED");
			}
		}
		return message;
	}

	static CurrentUser currentUser(StompHeaderAccessor accessor) {
		if (accessor.getUser() instanceof UsernamePasswordAuthenticationToken t
				&& t.getPrincipal() instanceof CurrentUser user) {
			return user;
		}
		throw new MessageDeliveryException("UNAUTHENTICATED");
	}
}
