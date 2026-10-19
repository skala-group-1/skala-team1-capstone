package com.skala.capstone.user;

import java.time.LocalDate;
import java.time.OffsetDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;

@Entity
@Table(name = "users", schema = "app")
public class User {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, unique = true)
	private String email;

	@Column(name = "password_hash", nullable = false)
	private String passwordHash;

	@Column(nullable = false)
	private String name;

	@Column(name = "birth_date")
	private LocalDate birthDate;

	private String gender;

	private String nationality;

	@Column(nullable = false)
	private String locale;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false)
	private Role role;

	@Column(name = "hospital_id")
	private Long hospitalId;

	@Column(name = "created_at", nullable = false)
	private OffsetDateTime createdAt;

	protected User() {
	}

	public static User newCustomer(String email, String passwordHash, String name, LocalDate birthDate,
			String gender, String nationality, String locale) {
		User u = new User();
		u.email = email;
		u.passwordHash = passwordHash;
		u.name = name;
		u.birthDate = birthDate;
		u.gender = gender;
		u.nationality = nationality;
		u.locale = locale;
		u.role = Role.CUSTOMER;
		u.createdAt = OffsetDateTime.now();
		return u;
	}

	public CurrentUser toCurrentUser() {
		return new CurrentUser(id, role, hospitalId, locale);
	}

	public Long getId() {
		return id;
	}

	public String getEmail() {
		return email;
	}

	public String getPasswordHash() {
		return passwordHash;
	}

	public String getName() {
		return name;
	}

	public LocalDate getBirthDate() {
		return birthDate;
	}

	public String getGender() {
		return gender;
	}

	public String getNationality() {
		return nationality;
	}

	public String getLocale() {
		return locale;
	}

	public Role getRole() {
		return role;
	}

	public Long getHospitalId() {
		return hospitalId;
	}

	public OffsetDateTime getCreatedAt() {
		return createdAt;
	}
}
