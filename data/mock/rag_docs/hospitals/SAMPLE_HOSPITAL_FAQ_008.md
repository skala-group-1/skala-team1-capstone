---
doc_id: SAMPLE_HOSPITAL_FAQ_008
title: "예담린 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 8
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 예담린 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 예담린 성형외과의원 안내: 통역 지원을 제공합니다. 방문 1영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 예담린 성형외과의원 안내: 상담만 받는 방문과 시술을 함께 희망하는 방문을 구분해 접수합니다. 예약 요청 시 원하는 방문 유형을 알려 주세요. 시술을 희망해도 당일 진행이 확정되는 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 예담린 성형외과의원 안내: 예약 요청 전에 앱 상담 채팅으로 상담 의제를 정리할 수 있습니다. 질문을 한 번에 모아 보내면 접수 담당자가 방문 준비 사항을 안내합니다. 원격으로 치료 계획을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 예담린 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 방문합니다. 복용 중인 약과 이전 시술 이력을 정리한 메모가 있다면 상담 시 의료진에게 전달합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 예담린 성형외과의원 안내: 온라인 견적은 확정 금액이 아닙니다. 대면 상담 후 시술 항목, 부가세 포함 여부, 약제비와 후속 방문 비용을 구분한 견적을 요청할 수 있습니다. 항목이 변경되면 다시 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 예담린 성형외과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 예담린 성형외과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 예담린 성형외과의원 안내: 방문 날짜 변경은 기존 예약 정보를 첨부해 앱 상담 채팅으로 문의합니다. 병원이 가능한 날짜를 안내한 뒤 필요한 취소 및 재예약 절차를 확인합니다. 새 요청만으로 기존 예약이 자동 취소되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 예담린 성형외과의원 안내: 상담 요약과 진료 관련 자료는 서로 구분해 신청합니다. 필요한 문서의 용도, 희망 언어, 귀국 날짜를 전달하면 발급 범위와 비용을 안내합니다. 일반 상담 채팅 답변이 공식 진료 문서를 대신하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 예담린 성형외과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 받고 담당자가 확인 후 연락 절차를 안내합니다. 문의를 보냈다는 이유만으로 후속 진료 예약이 생성되지는 않으며 별도 방문이 필요하면 일정을 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 예담린 성형외과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 예담린 성형외과의원 안내: 방문 최소 2영업일 전에 앱 상담 채팅으로 사용하는 보조기기와 동행 여부를 알려 주세요. 건물 진입, 엘리베이터, 상담 공간의 이동 경로를 확인한 뒤 안내합니다. 접근 가능 여부는 확인 전까지 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 예담린 성형외과의원 안내: 예약금 유무와 환불 비율은 이 안내만으로 확인할 수 없습니다. 예약 번호와 결제 여부를 알려 주고 본인 예약에 적용되는 취소 조건을 확인해야 합니다. 예약 취소 버튼을 눌렀다고 자동 환불된다고 안내하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 예담린 성형외과의원 (hospital_id=8)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 예담린 성형외과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_008_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
