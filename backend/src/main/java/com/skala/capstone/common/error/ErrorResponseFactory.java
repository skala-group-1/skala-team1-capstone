package com.skala.capstone.common.error;

import java.io.IOException;
import java.util.Locale;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.context.MessageSource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.common.web.TraceIdFilter;

/** 오류 응답 생성. 컨트롤러 예외(GlobalExceptionHandler)와 시큐리티 필터(401/403) 양쪽에서 같은 형식을 쓴다. */
@Component
public class ErrorResponseFactory {

	private final MessageSource messageSource;
	private final ObjectMapper objectMapper;

	public ErrorResponseFactory(MessageSource messageSource, ObjectMapper objectMapper) {
		this.messageSource = messageSource;
		this.objectMapper = objectMapper;
	}

	public ErrorResponse build(ErrorCode code, Map<String, Object> details, HttpServletRequest request) {
		String locale = RequestLocale.resolve(request);
		String message = messageSource.getMessage(code.messageKey(), null, code.name(), Locale.forLanguageTag(locale));
		return new ErrorResponse(code.name(), message, TraceIdFilter.current(), details == null ? Map.of() : details);
	}

	public void write(HttpServletResponse response, ErrorCode code, HttpServletRequest request) throws IOException {
		response.setStatus(code.status().value());
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.setCharacterEncoding("UTF-8");
		objectMapper.writeValue(response.getOutputStream(), build(code, Map.of(), request));
	}
}
