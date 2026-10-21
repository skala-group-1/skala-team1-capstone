---
doc_id: SAMPLE_HOSPITAL_FAQ_042
title: "보담엘 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 42
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 보담엘 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 보담엘 피부과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 보담엘 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 보담엘 피부과의원 안내: 방문 전 상담 채팅에서 안내 자료를 요청할 수 있습니다. 상담 채팅은 필요한 자료와 방문 절차를 확인하는 용도이며, 담당 의사와의 실시간 온라인 진료는 제공하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 보담엘 피부과의원 안내: 첫 방문은 예약 시각 20분 전부터 접수합니다. 예약 확인 메시지와 신분 확인용 여권을 준비하고, 동행인이 있다면 접수대에 함께 도착했다고 알려 주세요.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 보담엘 피부과의원 안내: 온라인 견적은 확정 금액이 아닙니다. 대면 상담 후 시술 항목, 부가세 포함 여부, 약제비와 후속 방문 비용을 구분한 견적을 요청할 수 있습니다. 항목이 변경되면 다시 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 보담엘 피부과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 보담엘 피부과의원 안내: 성인 동행인 최대 2명의 대기 공간 이용이 가능합니다. 상담실 동석은 1명까지 사전 요청할 수 있으며, 별도 통역 동행도 인원에 포함됩니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 보담엘 피부과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 보담엘 피부과의원 안내: 자료가 필요하면 귀국 최소 2영업일 전에 앱 상담 채팅으로 필요한 문서 종류와 언어를 알려 주세요. 발급 가능 여부, 본인 확인 방법, 수령 시점과 비용을 먼저 안내합니다. 모든 문서의 외국어 발급을 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 보담엘 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 받고 담당자가 확인 후 연락 절차를 안내합니다. 문의를 보냈다는 이유만으로 후속 진료 예약이 생성되지는 않으며 별도 방문이 필요하면 일정을 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 보담엘 피부과의원 안내: 기존 상담 자료나 참고 사진은 방문 시 보여 줄 수 있습니다. 온라인 제출이 필요하면 먼저 담당자에게 전달 방법을 확인합니다. 참고 사진은 동일 결과를 보장하는 자료로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 보담엘 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 보담엘 피부과의원 안내: 이 FAQ는 개별 예약의 환불 조건을 포함하지 않습니다. 결제 전 취소 가능한 시점, 환불 금액의 계산 기준, 처리 방법을 문서로 요청해 주세요. 정확한 금액은 해당 예약의 결제 조건을 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 보담엘 피부과의원 (hospital_id=42)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 보담엘 피부과의원 안내: 운영 시간 밖에도 앱 상담 채팅에 문의를 남길 수 있지만 다음 운영 시간부터 순서대로 확인합니다. 이 채팅은 실시간 의료 대응 창구가 아니며 접수 메시지가 의료진 확인 완료를 의미하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_042_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
