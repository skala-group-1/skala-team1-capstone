---
doc_id: SAMPLE_HOSPITAL_FAQ_012
title: "나린채 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 12
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 나린채 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 나린채 성형외과의원 안내: 통역 지원을 제공합니다. 방문 2영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 나린채 성형외과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 나린채 성형외과의원 안내: 예약 요청 전에 앱 상담 채팅으로 상담 의제를 정리할 수 있습니다. 질문을 한 번에 모아 보내면 접수 담당자가 방문 준비 사항을 안내합니다. 원격으로 치료 계획을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 나린채 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 10분 전에 접수합니다. 이전 상담 자료가 있다면 원본 파일 또는 사본을 지참할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 나린채 성형외과의원 안내: 대면 상담 후 항목별 견적서를 요청할 수 있습니다. 시술비, 부가세 포함 여부, 별도로 청구되는 항목을 확인한 뒤 진행 여부를 결정합니다. 온라인 안내 가격은 확정 가격이 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 나린채 성형외과의원 안내: 지각이 예상되면 예약 확인 메시지와 예상 도착 시각을 앱 상담 채팅에 보내 주세요. 도착 후 당일 상담 순서를 다시 안내하며 원래 예약 순서가 유지된다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 나린채 성형외과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 나린채 성형외과의원 안내: 앱 상담 채팅에 기존 예약 정보와 변경 희망 날짜 2개를 보내 주세요. 병원이 가능한 일정을 안내한 뒤 기존 예약 처리와 새 예약 절차를 확인합니다. 메시지를 보낸 것만으로 날짜가 바뀌지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 나린채 성형외과의원 안내: 상담 요약과 진료 관련 자료는 서로 구분해 신청합니다. 필요한 문서의 용도, 희망 언어, 귀국 날짜를 전달하면 발급 범위와 비용을 안내합니다. 일반 상담 채팅 답변이 공식 진료 문서를 대신하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 나린채 성형외과의원 안내: 귀국 이후에는 앱 상담 채팅에 예약 정보와 질문을 남겨 주세요. 필요한 사진은 담당자가 요청한 경우에 전달합니다. 답변은 후속 상담 절차 안내이며 채팅으로 진단을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 나린채 성형외과의원 안내: 본인이 상담받을 부위의 참고 사진은 담당자 안내에 따라 제출합니다. 여권 사본이나 결제 카드 사진을 일반 상담 자료로 보내지 마세요. 진료 공간 촬영은 현장 허가가 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 나린채 성형외과의원 안내: 예약 요청 시 계단 이용의 어려움과 필요한 이동 지원을 적어 주세요. 접수 담당자가 이동 경로와 동행 필요 사항을 확인해 안내합니다. 별도 이동 보조 인력 제공은 확정된 서비스가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 나린채 성형외과의원 안내: 항공편 변경이나 일정 취소에 따른 환불 가능 여부는 이 FAQ에 정의되어 있지 않습니다. 예약 정보와 결제 내역을 바탕으로 병원에 적용 조건을 확인합니다. 예외적인 전액 환불을 약속하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 나린채 성형외과의원 (hospital_id=12)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 나린채 성형외과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_012_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
