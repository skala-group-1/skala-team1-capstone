package com.skala.capstone.common.web;

import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** DB 커밋 뒤에 실행 (STOMP 푸시 등). 트랜잭션 밖이면 즉시 실행. */
public final class AfterCommit {

	private AfterCommit() {
	}

	public static void run(Runnable action) {
		if (TransactionSynchronizationManager.isSynchronizationActive()) {
			TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
				@Override
				public void afterCommit() {
					action.run();
				}
			});
		} else {
			action.run();
		}
	}
}
