package com.skala.capstone.docs;

import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.web.TraceIdFilter;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * 근거 문서 원문 (AI 답변의 근거 칩 → 원문 패널). 07 문서 5장 / 04 문서 3장:
 * backend → agent GET /internal/resources?uri=doc://{docId}[/sections/{section}] → rag-mcp Resource.
 * agent 응답 JSON 을 그대로 전달한다. agent 가 없거나 느리면(3초) 503 AI_UNAVAILABLE.
 */
@Tag(name = "Docs")
@RestController
@RequestMapping("/api/docs")
public class DocsController {

	private static final Logger log = LoggerFactory.getLogger(DocsController.class);
	private static final Pattern SAFE = Pattern.compile("[A-Za-z0-9_.\\-]{1,100}");

	private final RestClient agent;
	private final String serviceToken;

	public DocsController(AppProperties app) {
		SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
		factory.setConnectTimeout(app.agent().timeout());
		factory.setReadTimeout(app.agent().timeout());
		this.agent = RestClient.builder().baseUrl(app.agent().baseUrl()).requestFactory(factory).build();
		this.serviceToken = app.serviceToken();
	}

	@Operation(summary = "근거 문서 원문 (doc://{docId}, section 지정 시 그 섹션만)")
	@GetMapping("/{docId}")
	public JsonNode doc(@PathVariable String docId, @RequestParam(required = false) String section) {
		if (!SAFE.matcher(docId).matches() || (section != null && !SAFE.matcher(section).matches())) {
			throw ApiException.notFound("doc");
		}
		String uri = "doc://" + docId + (section == null ? "" : "/sections/" + section);
		try {
			return agent.get().uri(b -> b.path("/internal/resources").queryParam("uri", uri).build())
					.header("X-Service-Token", serviceToken)
					.header(TraceIdFilter.HEADER, String.valueOf(TraceIdFilter.current()))
					.retrieve().body(JsonNode.class);
		} catch (HttpClientErrorException e) {
			if (e.getStatusCode() == HttpStatus.NOT_FOUND) {
				throw ApiException.notFound("doc");
			}
			log.warn("agent resource error {} for {}", e.getStatusCode(), uri);
			throw new ApiException(ErrorCode.AI_UNAVAILABLE);
		} catch (RestClientException e) {
			log.warn("agent unreachable for {}: {}", uri, e.getMessage());
			throw new ApiException(ErrorCode.AI_UNAVAILABLE);
		}
	}
}
