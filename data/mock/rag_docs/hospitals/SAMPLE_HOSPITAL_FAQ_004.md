---
doc_id: SAMPLE_HOSPITAL_FAQ_004
title: "서린 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 4
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 서린 피부과의원 (hospital_id=4)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 서린 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 서린 피부과의원 (hospital_id=4)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 서린 피부과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 1영업일 전까지 예약 요청 내용에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 서린 피부과의원 (hospital_id=4)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 서린 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 서린 피부과의원 (hospital_id=4)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 서린 피부과의원 안내: 온라인 사전 문의는 텍스트 상담으로 받습니다. 관심 부위, 이전 상담 여부, 한국 체류 기간을 적어 주세요. 의료진의 대면 진찰을 대신하는 진료 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 서린 피부과의원 (hospital_id=4)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 서린 피부과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 접수합니다. 상담 질문을 미리 적어 오면 접수 시 함께 전달할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 서린 피부과의원 (hospital_id=4)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 서린 피부과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 서린 피부과의원 (hospital_id=4)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 서린 피부과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 서린 피부과의원 (hospital_id=4)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 서린 피부과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 서린 피부과의원 (hospital_id=4)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 서린 피부과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 서린 피부과의원 (hospital_id=4)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 서린 피부과의원 안내: 자료가 필요하면 귀국 최소 2영업일 전에 앱 상담 채팅으로 필요한 문서 종류와 언어를 알려 주세요. 발급 가능 여부, 본인 확인 방법, 수령 시점과 비용을 먼저 안내합니다. 모든 문서의 외국어 발급을 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 서린 피부과의원 (hospital_id=4)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 서린 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 받고 담당자가 확인 후 연락 절차를 안내합니다. 문의를 보냈다는 이유만으로 후속 진료 예약이 생성되지는 않으며 별도 방문이 필요하면 일정을 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 서린 피부과의원 (hospital_id=4)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 서린 피부과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 서린 피부과의원 (hospital_id=4)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 서린 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 서린 피부과의원 (hospital_id=4)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 서린 피부과의원 안내: 예약금과 취소 수수료의 세부 기준은 미확인 항목입니다. 결제 전에 병원의 서면 조건을 받으세요. 예약 취소 요청, 취소 완료, 환불 완료 여부는 각각 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 서린 피부과의원 (hospital_id=4)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 서린 피부과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_004_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
