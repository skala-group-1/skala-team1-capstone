package com.skala.capstone.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;

/** Swagger UI: http://localhost:8080/swagger-ui — 로그인 응답의 accessToken 을 Authorize 에 넣어 테스트. */
@Configuration
public class OpenApiConfig {

	@Bean
	OpenAPI openApi() {
		return new OpenAPI()
				.info(new Info().title("SKALA team1 capstone backend").version("v1"))
				.components(new Components()
						.addSecuritySchemes("bearer", new SecurityScheme().type(SecurityScheme.Type.HTTP)
								.scheme("bearer").bearerFormat("JWT"))
						.addSecuritySchemes("serviceToken", new SecurityScheme().type(SecurityScheme.Type.APIKEY)
								.in(SecurityScheme.In.HEADER).name("X-Service-Token"))
						.addSecuritySchemes("actingUser", new SecurityScheme().type(SecurityScheme.Type.APIKEY)
								.in(SecurityScheme.In.HEADER).name("X-Acting-User-Id")))
				.addSecurityItem(new SecurityRequirement().addList("bearer"))
				.addSecurityItem(new SecurityRequirement().addList("serviceToken").addList("actingUser"));
	}
}
