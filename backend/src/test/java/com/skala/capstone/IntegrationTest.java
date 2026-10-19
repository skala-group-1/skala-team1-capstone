package com.skala.capstone;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.rabbitmq.RabbitMQContainer;
import org.testcontainers.utility.DockerImageName;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * 실제 PostgreSQL(pgvector:pg16) + RabbitMQ 컨테이너로 테스트한다 (Flyway: V1 schema → V2 → V100 seed → V101).
 * 컨테이너·DB 는 모든 테스트 클래스가 공유하므로, 데이터를 바꾸는 테스트는 서로 다른 병원·슬롯·사용자를 쓴다.
 * 서버는 실제 포트로 떠서 STOMP·SSE 도 테스트할 수 있다. Docker 가 실행 중이어야 한다.
 */
@Tag("integration")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@ActiveProfiles("test")
public abstract class IntegrationTest {

	static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer(
			DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
			.withDatabaseName("capstone").withUsername("capstone").withPassword("capstone");

	static final RabbitMQContainer RABBIT = new RabbitMQContainer(DockerImageName.parse("rabbitmq:3-management"));

	static {
		POSTGRES.start();
		RABBIT.start();
	}

	@DynamicPropertySource
	static void datasource(DynamicPropertyRegistry registry) {
		registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
		registry.add("spring.datasource.username", POSTGRES::getUsername);
		registry.add("spring.datasource.password", POSTGRES::getPassword);
		registry.add("spring.rabbitmq.host", RABBIT::getHost);
		registry.add("spring.rabbitmq.port", RABBIT::getAmqpPort);
		registry.add("spring.rabbitmq.username", RABBIT::getAdminUsername);
		registry.add("spring.rabbitmq.password", RABBIT::getAdminPassword);
	}

	protected static final String DEMO_PASSWORD = "Passw0rd!";

	@Autowired
	protected MockMvc mvc;

	@Autowired
	protected ObjectMapper objectMapper;

	@Autowired
	protected JdbcClient jdbc;

	@Autowired
	protected org.springframework.amqp.rabbit.core.RabbitTemplate rabbit;

	@org.springframework.boot.test.web.server.LocalServerPort
	protected int port;

	/**
	 * 가짜 agent: 큐에서 조건에 맞는 메시지 1건을 꺼낸다 (최대 10초). 다른 테스트가 남긴 메시지는 버린다.
	 */
	protected JsonNode receiveFrom(String queue, java.util.function.Predicate<JsonNode> match) throws Exception {
		long deadline = System.currentTimeMillis() + 10_000;
		while (System.currentTimeMillis() < deadline) {
			org.springframework.amqp.core.Message m = rabbit.receive(queue, 500);
			if (m != null) {
				JsonNode body = objectMapper.readTree(m.getBody());
				if (match.test(body)) {
					return body;
				}
			}
		}
		throw new AssertionError("no matching message on " + queue);
	}

	/** 조건이 참이 될 때까지 최대 10초 기다린다 (큐 처리 같은 비동기 결과 확인용) */
	protected void await(java.util.function.BooleanSupplier condition, String what) throws InterruptedException {
		for (int i = 0; i < 100; i++) {
			if (condition.getAsBoolean()) {
				return;
			}
			Thread.sleep(100);
		}
		throw new AssertionError("timed out waiting: " + what);
	}

	protected MvcResult login(String email) throws Exception {
		return mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("email", email, "password", DEMO_PASSWORD))))
				.andExpect(status().isOk()).andReturn();
	}

	protected String accessToken(String email) throws Exception {
		return "Bearer " + body(login(email)).get("accessToken").asText();
	}

	protected JsonNode body(MvcResult result) throws Exception {
		return objectMapper.readTree(result.getResponse().getContentAsByteArray());
	}

	protected String json(Object value) throws Exception {
		return objectMapper.writeValueAsString(value);
	}
}
