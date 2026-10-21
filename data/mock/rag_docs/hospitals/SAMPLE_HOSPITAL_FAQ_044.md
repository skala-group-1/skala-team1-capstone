---
doc_id: SAMPLE_HOSPITAL_FAQ_044
title: "비채 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 44
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 비채 피부과의원 (hospital_id=44)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 비채 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 비채 피부과의원 (hospital_id=44)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 비채 피부과의원 안내: 통역 지원을 제공합니다. 방문 5영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 비채 피부과의원 (hospital_id=44)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 비채 피부과의원 안내: 첫 방문은 상담 전용으로 접수합니다. 시술을 원하면 대면 상담 뒤 별도의 일정 안내를 받습니다. 상담을 받았다는 이유만으로 시술 예약이 생성되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 비채 피부과의원 (hospital_id=44)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 비채 피부과의원 안내: 방문 전 앱 상담 채팅으로 관심 시술과 질문을 전달할 수 있습니다. 답변은 방문 준비와 상담 절차 안내이며 사진만으로 진단하거나 시술 가능 여부를 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 비채 피부과의원 (hospital_id=44)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 비채 피부과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 접수합니다. 상담 질문을 미리 적어 오면 접수 시 함께 전달할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 비채 피부과의원 (hospital_id=44)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 비채 피부과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 비채 피부과의원 (hospital_id=44)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 비채 피부과의원 안내: 예약 시각보다 15분 이상 늦으면 접수 담당자가 당일 상담 가능 여부를 다시 확인합니다. 지각이 예상될 때는 앱 상담 채팅에 먼저 알려 주세요. 가능한 시간이 없으면 일정 변경을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 비채 피부과의원 (hospital_id=44)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 비채 피부과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 비채 피부과의원 (hospital_id=44)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 비채 피부과의원 안내: 앱 상담 채팅에 기존 예약 정보와 변경 희망 날짜 2개를 보내 주세요. 병원이 가능한 일정을 안내한 뒤 기존 예약 처리와 새 예약 절차를 확인합니다. 메시지를 보낸 것만으로 날짜가 바뀌지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 비채 피부과의원 (hospital_id=44)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 비채 피부과의원 안내: 자료가 필요하면 귀국 최소 2영업일 전에 앱 상담 채팅으로 필요한 문서 종류와 언어를 알려 주세요. 발급 가능 여부, 본인 확인 방법, 수령 시점과 비용을 먼저 안내합니다. 모든 문서의 외국어 발급을 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 비채 피부과의원 (hospital_id=44)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 비채 피부과의원 안내: 귀국 후에도 앱 상담 채팅으로 방문 날짜와 문의 내용을 보낼 수 있습니다. 담당자가 기록을 확인해 후속 연락 절차를 안내합니다. 채팅만으로 진단이나 처방을 제공하는 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 비채 피부과의원 (hospital_id=44)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 비채 피부과의원 안내: 첫 온라인 문의에는 사진을 첨부하지 않고 상담 내용을 텍스트로 보내 주세요. 필요한 자료는 담당자가 안내합니다. 방문 중 의료진이나 다른 방문객이 보이는 촬영은 허가 없이 진행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 비채 피부과의원 (hospital_id=44)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 비채 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 비채 피부과의원 (hospital_id=44)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 비채 피부과의원 안내: 이 FAQ에는 예약금 금액과 취소 시점별 환불 기준이 등록되어 있지 않습니다. 결제 전 앱 상담 채팅으로 예약금 유무와 환불 조건을 서면으로 요청해 주세요. 앱의 예약 취소와 결제 금액 환불 처리는 같은 절차로 단정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 비채 피부과의원 (hospital_id=44)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 비채 피부과의원 안내: 야간이나 휴무일의 채팅은 접수만 가능하고 담당자 답변은 다음 운영 시간에 진행합니다. 답변 시각을 확정적으로 보장하지 않으며 급한 의료 상황의 대응 수단으로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_044_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
