package com.skala.capstone.user;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

public interface UserRepository extends JpaRepository<User, Long> {

	Optional<User> findByEmailIgnoreCase(String email);

	boolean existsByEmailIgnoreCase(String email);

	@Modifying
	@Query("update User u set u.passwordHash = :hash where u.passwordHash = :placeholder")
	int replacePasswordPlaceholder(String placeholder, String hash);
}
