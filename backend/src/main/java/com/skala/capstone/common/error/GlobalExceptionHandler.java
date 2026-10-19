package com.skala.capstone.common.error;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;

@RestControllerAdvice
public class GlobalExceptionHandler {

	private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

	private final ErrorResponseFactory errors;
	private final AuditLogger audit;

	public GlobalExceptionHandler(ErrorResponseFactory errors, AuditLogger audit) {
		this.errors = errors;
		this.audit = audit;
	}

	@ExceptionHandler(ApiException.class)
	ResponseEntity<ErrorResponse> handleApi(ApiException e, HttpServletRequest request) {
		if (e.code() == ErrorCode.ACCESS_DENIED) {
			auditAccessDenied(request);
		}
		return respond(e.code(), e.details(), request);
	}

	/** @PreAuthorize 거부는 컨트롤러 단에서 던져지므로 여기서 403 + 감사 로그 */
	@ExceptionHandler(AccessDeniedException.class)
	ResponseEntity<ErrorResponse> handleAccessDenied(AccessDeniedException e, HttpServletRequest request) {
		auditAccessDenied(request);
		return respond(ErrorCode.ACCESS_DENIED, Map.of(), request);
	}

	@ExceptionHandler(MethodArgumentNotValidException.class)
	ResponseEntity<ErrorResponse> handleBodyValidation(MethodArgumentNotValidException e, HttpServletRequest request) {
		List<Map<String, String>> fields = new ArrayList<>();
		for (FieldError fe : e.getBindingResult().getFieldErrors()) {
			fields.add(Map.of("field", fe.getField(), "reason", String.valueOf(fe.getDefaultMessage())));
		}
		return respond(ErrorCode.VALIDATION_FAILED, Map.of("fields", fields), request);
	}

	@ExceptionHandler(HandlerMethodValidationException.class)
	ResponseEntity<ErrorResponse> handleParamValidation(HandlerMethodValidationException e, HttpServletRequest request) {
		List<Map<String, String>> fields = new ArrayList<>();
		e.getParameterValidationResults().forEach(r -> r.getResolvableErrors().forEach(err -> fields.add(Map.of(
				"field", String.valueOf(r.getMethodParameter().getParameterName()),
				"reason", String.valueOf(err.getDefaultMessage())))));
		return respond(ErrorCode.VALIDATION_FAILED, Map.of("fields", fields), request);
	}

	@ExceptionHandler(MissingServletRequestParameterException.class)
	ResponseEntity<ErrorResponse> handleMissingParam(MissingServletRequestParameterException e, HttpServletRequest request) {
		return fieldError(e.getParameterName(), "required", request);
	}

	@ExceptionHandler(MissingRequestHeaderException.class)
	ResponseEntity<ErrorResponse> handleMissingHeader(MissingRequestHeaderException e, HttpServletRequest request) {
		return fieldError(e.getHeaderName(), "required header", request);
	}

	@ExceptionHandler(MethodArgumentTypeMismatchException.class)
	ResponseEntity<ErrorResponse> handleTypeMismatch(MethodArgumentTypeMismatchException e, HttpServletRequest request) {
		return fieldError(e.getName(), "invalid value", request);
	}

	@ExceptionHandler(HttpMessageNotReadableException.class)
	ResponseEntity<ErrorResponse> handleUnreadable(HttpMessageNotReadableException e, HttpServletRequest request) {
		return fieldError("body", "malformed JSON or invalid value", request);
	}

	@ExceptionHandler(NoResourceFoundException.class)
	ResponseEntity<ErrorResponse> handleNoResource(NoResourceFoundException e, HttpServletRequest request) {
		return respond(ErrorCode.NOT_FOUND, Map.of("resource", e.getResourcePath()), request);
	}

	@ExceptionHandler(HttpRequestMethodNotSupportedException.class)
	ResponseEntity<ErrorResponse> handleMethod(HttpRequestMethodNotSupportedException e, HttpServletRequest request) {
		return respond(ErrorCode.NOT_FOUND, Map.of("resource", request.getRequestURI()), request);
	}

	@ExceptionHandler(Exception.class)
	ResponseEntity<ErrorResponse> handleUnexpected(Exception e, HttpServletRequest request) {
		log.error("unhandled error on {} {}", request.getMethod(), request.getRequestURI(), e);
		return respond(ErrorCode.INTERNAL_ERROR, Map.of(), request);
	}

	private ResponseEntity<ErrorResponse> fieldError(String field, String reason, HttpServletRequest request) {
		return respond(ErrorCode.VALIDATION_FAILED,
				Map.of("fields", List.of(Map.of("field", field, "reason", reason))), request);
	}

	private ResponseEntity<ErrorResponse> respond(ErrorCode code, Map<String, Object> details, HttpServletRequest request) {
		return ResponseEntity.status(code.status()).body(errors.build(code, details, request));
	}

	private void auditAccessDenied(HttpServletRequest request) {
		audit.log(CurrentUser.current().orElse(null), "ACCESS_DENIED",
				request.getMethod() + " " + request.getRequestURI(), Map.of());
	}
}
