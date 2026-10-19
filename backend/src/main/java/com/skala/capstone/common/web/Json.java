package com.skala.capstone.common.web;

import org.springframework.stereotype.Component;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/** jsonb 컬럼 ↔ Java 값 변환 도우미. */
@Component
public class Json {

	private final ObjectMapper objectMapper;

	public Json(ObjectMapper objectMapper) {
		this.objectMapper = objectMapper;
	}

	public String write(Object value) {
		if (value == null) {
			return null;
		}
		try {
			return objectMapper.writeValueAsString(value);
		} catch (JsonProcessingException e) {
			throw new IllegalArgumentException("not serializable to JSON", e);
		}
	}

	/** jsonb 문자열 → JsonNode (null 이면 null). 응답에 그대로 실어 보낼 때 사용. */
	public JsonNode read(String json) {
		if (json == null) {
			return null;
		}
		try {
			return objectMapper.readTree(json);
		} catch (JsonProcessingException e) {
			throw new IllegalStateException("invalid JSON in DB", e);
		}
	}

	public <T> T convert(Object value, Class<T> type) {
		return objectMapper.convertValue(value, type);
	}

	public ObjectMapper mapper() {
		return objectMapper;
	}
}
