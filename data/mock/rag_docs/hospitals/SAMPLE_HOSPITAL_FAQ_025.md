---
doc_id: SAMPLE_HOSPITAL_FAQ_025
title: "이든솔 성형외과·피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 25
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 이든솔 성형외과·피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 이든솔 성형외과·피부과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 이든솔 성형외과·피부과의원 안내: 첫 방문은 상담 전용으로 접수합니다. 시술을 원하면 대면 상담 뒤 별도의 일정 안내를 받습니다. 상담을 받았다는 이유만으로 시술 예약이 생성되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 이든솔 성형외과·피부과의원 안내: 방문 전 상담 채팅에서 안내 자료를 요청할 수 있습니다. 상담 채팅은 필요한 자료와 방문 절차를 확인하는 용도이며, 담당 의사와의 실시간 온라인 진료는 제공하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 이든솔 성형외과·피부과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 방문합니다. 복용 중인 약과 이전 시술 이력을 정리한 메모가 있다면 상담 시 의료진에게 전달합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 이든솔 성형외과·피부과의원 안내: 온라인 견적에는 견적 대상 시술과 포함 항목을 함께 안내합니다. 대면 상담에서 계획이 바뀌면 새 견적을 확인해야 하며, 기존 안내만으로 최종 결제 금액이 확정되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 이든솔 성형외과·피부과의원 안내: 예약 시각을 넘길 것 같으면 앱 상담 채팅으로 먼저 연락해 주세요. 20분 이상 늦는 경우 당일 상담 가능 여부를 다시 확인하며, 가능한 시간이 없으면 다른 일정을 안내합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 이든솔 성형외과·피부과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 이든솔 성형외과·피부과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 이든솔 성형외과·피부과의원 안내: 귀국 최소 3영업일 전에 필요한 자료와 수령 희망일을 앱 상담 채팅으로 알려 주세요. 온라인 전달 가능 여부와 직접 수령 필요 여부를 구분해 안내하며 외국어 번역은 별도 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 이든솔 성형외과·피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 받고 담당자가 확인 후 연락 절차를 안내합니다. 문의를 보냈다는 이유만으로 후속 진료 예약이 생성되지는 않으며 별도 방문이 필요하면 일정을 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 이든솔 성형외과·피부과의원 안내: 기존 상담 자료나 참고 사진은 방문 시 보여 줄 수 있습니다. 온라인 제출이 필요하면 먼저 담당자에게 전달 방법을 확인합니다. 참고 사진은 동일 결과를 보장하는 자료로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 이든솔 성형외과·피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 이든솔 성형외과·피부과의원 안내: 이 FAQ에는 예약금 금액과 취소 시점별 환불 기준이 등록되어 있지 않습니다. 결제 전 앱 상담 채팅으로 예약금 유무와 환불 조건을 서면으로 요청해 주세요. 앱의 예약 취소와 결제 금액 환불 처리는 같은 절차로 단정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 이든솔 성형외과·피부과의원 (hospital_id=25)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 이든솔 성형외과·피부과의원 안내: 야간이나 휴무일의 채팅은 접수만 가능하고 담당자 답변은 다음 운영 시간에 진행합니다. 답변 시각을 확정적으로 보장하지 않으며 급한 의료 상황의 대응 수단으로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_025_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
