---
doc_id: SAMPLE_HOSPITAL_FAQ_036
title: "윤슬빛 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 36
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 윤슬빛 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 윤슬빛 성형외과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 윤슬빛 성형외과의원 안내: 첫 방문은 상담 전용으로 접수합니다. 시술을 원하면 대면 상담 뒤 별도의 일정 안내를 받습니다. 상담을 받았다는 이유만으로 시술 예약이 생성되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 윤슬빛 성형외과의원 안내: 방문 전에는 앱 상담 채팅으로 질문 목록과 방문 희망 기간을 접수합니다. 사진 자료는 담당자가 요청했을 때 전달합니다. 별도 화상 상담은 운영하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 윤슬빛 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 방문합니다. 복용 중인 약과 이전 시술 이력을 정리한 메모가 있다면 상담 시 의료진에게 전달합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 윤슬빛 성형외과의원 안내: 온라인 견적과 실제 결제 금액은 상담 결과에 따라 달라질 수 있습니다. 두 가지 이상을 상담한 경우 항목별 견적과 함께 진행하는 견적을 구분해 요청할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 윤슬빛 성형외과의원 안내: 예약 시각보다 15분 이상 늦으면 접수 담당자가 당일 상담 가능 여부를 다시 확인합니다. 지각이 예상될 때는 앱 상담 채팅에 먼저 알려 주세요. 가능한 시간이 없으면 일정 변경을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 윤슬빛 성형외과의원 안내: 성인 동행인 최대 2명의 대기 공간 이용이 가능합니다. 상담실 동석은 1명까지 사전 요청할 수 있으며, 별도 통역 동행도 인원에 포함됩니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 윤슬빛 성형외과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 윤슬빛 성형외과의원 안내: 자료 발급은 방문 당일 접수대 또는 앱 상담 채팅에서 신청합니다. 문서 종류에 따라 준비 기간이 다르므로 귀국 일정을 함께 전달해 주세요. 본인 확인과 비용 안내를 받은 후 수령 절차를 진행합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 윤슬빛 성형외과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 윤슬빛 성형외과의원 안내: 첫 온라인 문의에는 사진을 첨부하지 않고 상담 내용을 텍스트로 보내 주세요. 필요한 자료는 담당자가 안내합니다. 방문 중 의료진이나 다른 방문객이 보이는 촬영은 허가 없이 진행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 윤슬빛 성형외과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 윤슬빛 성형외과의원 안내: 항공편 변경이나 일정 취소에 따른 환불 가능 여부는 이 FAQ에 정의되어 있지 않습니다. 예약 정보와 결제 내역을 바탕으로 병원에 적용 조건을 확인합니다. 예외적인 전액 환불을 약속하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 윤슬빛 성형외과의원 (hospital_id=36)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 윤슬빛 성형외과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_036_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
