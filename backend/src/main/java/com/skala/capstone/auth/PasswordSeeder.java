package com.skala.capstone.auth;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.user.UserRepository;

/**
 * mock 사용자(V100__seed.sql)의 password_hash 는 '{bcrypt}PLACEHOLDER' 로 들어온다.
 * 기동 시 데모 비밀번호를 BCrypt 로 해시해 채운다. 이미 해시된 계정·가입한 계정은 건드리지 않는다.
 */
@Component
public class PasswordSeeder implements ApplicationRunner {

	static final String PLACEHOLDER = "{bcrypt}PLACEHOLDER";
	private static final Logger log = LoggerFactory.getLogger(PasswordSeeder.class);

	private final UserRepository users;
	private final PasswordEncoder passwordEncoder;
	private final AppProperties app;

	public PasswordSeeder(UserRepository users, PasswordEncoder passwordEncoder, AppProperties app) {
		this.users = users;
		this.passwordEncoder = passwordEncoder;
		this.app = app;
	}

	@Override
	@Transactional
	public void run(ApplicationArguments args) {
		int updated = users.replacePasswordPlaceholder(PLACEHOLDER, passwordEncoder.encode(app.seed().demoPassword()));
		if (updated > 0) {
			log.info("PasswordSeeder: set demo password for {} seed users", updated);
		}
	}
}
