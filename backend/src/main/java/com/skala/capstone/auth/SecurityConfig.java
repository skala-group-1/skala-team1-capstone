package com.skala.capstone.auth;

import java.util.List;

import jakarta.servlet.DispatcherType;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ErrorResponseFactory;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.user.UserRepository;

/** 11 문서 2장: CORS → JWT → 내부 서비스 토큰 → URL 역할 → @PreAuthorize → 서비스 소유권 검사. */
@Configuration
@EnableMethodSecurity
public class SecurityConfig {

	@Bean
	SecurityFilterChain securityFilterChain(HttpSecurity http, JwtProvider jwt, UserRepository users,
			ErrorResponseFactory errors, AuditLogger audit, AppProperties app) throws Exception {
		http
				.csrf(AbstractHttpConfigurer::disable)
				.cors(cors -> cors.configurationSource(corsConfigurationSource(app)))
				.sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				.httpBasic(AbstractHttpConfigurer::disable)
				.formLogin(AbstractHttpConfigurer::disable)
				.logout(AbstractHttpConfigurer::disable)
				.authorizeHttpRequests(auth -> auth
						// SSE 응답 마무리(ASYNC)·오류 페이지(ERROR) 재진입은 이미 인증된 요청의 연장이므로 통과
						.dispatcherTypeMatchers(DispatcherType.ASYNC, DispatcherType.ERROR).permitAll()
						.requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
						.requestMatchers("/api/auth/**").permitAll()
						.requestMatchers("/swagger-ui/**", "/swagger-ui.html", "/v3/api-docs/**").permitAll()
						.requestMatchers("/error").permitAll()
						// WebSocket 핸드셰이크는 열어 두고, 인증은 STOMP CONNECT 프레임에서 한다 (StompAuthInterceptor)
						.requestMatchers("/ws", "/ws/**").permitAll()
						.requestMatchers("/api/counselor/**").hasRole("COUNSELOR")
						.requestMatchers("/api/hospital-admin/**").hasRole("HOSPITAL_ADMIN")
						.requestMatchers("/api/ops/**").hasRole("OPERATOR")
						// /internal/** 는 InternalServiceTokenFilter 가 서비스 토큰 + acting user 로 인증
						.requestMatchers("/internal/**").authenticated()
						.requestMatchers("/api/**").authenticated()
						.anyRequest().denyAll())
				.exceptionHandling(e -> e
						.authenticationEntryPoint(new RestAuthenticationEntryPoint(errors))
						.accessDeniedHandler(new RestAccessDeniedHandler(errors, audit)))
				.addFilterBefore(new JwtAuthenticationFilter(jwt), UsernamePasswordAuthenticationFilter.class)
				.addFilterAfter(new InternalServiceTokenFilter(app.serviceToken(), users, errors),
						JwtAuthenticationFilter.class);
		return http.build();
	}

	@Bean
	PasswordEncoder passwordEncoder() {
		return new BCryptPasswordEncoder(10);
	}

	private CorsConfigurationSource corsConfigurationSource(AppProperties app) {
		CorsConfiguration config = new CorsConfiguration();
		config.setAllowedOrigins(app.cors().allowedOrigins());
		config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
		config.setAllowedHeaders(List.of("*"));
		config.setExposedHeaders(List.of("X-Trace-Id"));
		config.setAllowCredentials(true);
		UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
		source.registerCorsConfiguration("/**", config);
		return source;
	}
}
