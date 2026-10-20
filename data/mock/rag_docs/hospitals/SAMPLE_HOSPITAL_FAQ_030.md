---
doc_id: SAMPLE_HOSPITAL_FAQ_030
title: "오델린 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 30
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 오델린 피부과의원 (hospital_id=30)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 오델린 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 오델린 피부과의원 (hospital_id=30)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 오델린 피부과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 5영업일 전까지 예약 요청 내용에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 오델린 피부과의원 (hospital_id=30)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 오델린 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 오델린 피부과의원 (hospital_id=30)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 오델린 피부과의원 안내: 방문 전 앱 상담 채팅으로 관심 시술과 질문을 전달할 수 있습니다. 답변은 방문 준비와 상담 절차 안내이며 사진만으로 진단하거나 시술 가능 여부를 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 오델린 피부과의원 (hospital_id=30)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 오델린 피부과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 10분 전에 접수합니다. 이전 상담 자료가 있다면 원본 파일 또는 사본을 지참할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 오델린 피부과의원 (hospital_id=30)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 오델린 피부과의원 안내: 온라인 견적은 확정 금액이 아닙니다. 대면 상담 후 시술 항목, 부가세 포함 여부, 약제비와 후속 방문 비용을 구분한 견적을 요청할 수 있습니다. 항목이 변경되면 다시 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 오델린 피부과의원 (hospital_id=30)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 오델린 피부과의원 안내: 예약 시각을 넘길 것 같으면 앱 상담 채팅으로 먼저 연락해 주세요. 20분 이상 늦는 경우 당일 상담 가능 여부를 다시 확인하며, 가능한 시간이 없으면 다른 일정을 안내합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 오델린 피부과의원 (hospital_id=30)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 오델린 피부과의원 안내: 동행인은 대기 공간을 이용할 수 있습니다. 상담실 동석을 원하면 방문 전에 앱 상담 채팅으로 요청하고 병원 확인을 받아야 합니다. 시술 공간에는 이 안내만으로 동행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 오델린 피부과의원 (hospital_id=30)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 오델린 피부과의원 안내: 새로운 날짜가 필요하면 앱 상담 채팅에 기존 예약과 변경 사유를 남겨 주세요. 이용 가능한 시간은 업무 조회로 확인하고, 병원이 안내한 예약 변경 절차를 진행합니다. 동일 의료진 배정은 별도 확인 사항입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 오델린 피부과의원 (hospital_id=30)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 오델린 피부과의원 안내: 자료가 필요하면 귀국 최소 2영업일 전에 앱 상담 채팅으로 필요한 문서 종류와 언어를 알려 주세요. 발급 가능 여부, 본인 확인 방법, 수령 시점과 비용을 먼저 안내합니다. 모든 문서의 외국어 발급을 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 오델린 피부과의원 (hospital_id=30)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 오델린 피부과의원 안내: 귀국 후에도 앱 상담 채팅으로 방문 날짜와 문의 내용을 보낼 수 있습니다. 담당자가 기록을 확인해 후속 연락 절차를 안내합니다. 채팅만으로 진단이나 처방을 제공하는 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 오델린 피부과의원 (hospital_id=30)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 오델린 피부과의원 안내: 본인이 상담받을 부위의 참고 사진은 담당자 안내에 따라 제출합니다. 여권 사본이나 결제 카드 사진을 일반 상담 자료로 보내지 마세요. 진료 공간 촬영은 현장 허가가 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 오델린 피부과의원 (hospital_id=30)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 오델린 피부과의원 안내: 예약 요청 시 계단 이용의 어려움과 필요한 이동 지원을 적어 주세요. 접수 담당자가 이동 경로와 동행 필요 사항을 확인해 안내합니다. 별도 이동 보조 인력 제공은 확정된 서비스가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 오델린 피부과의원 (hospital_id=30)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 오델린 피부과의원 안내: 예약금과 취소 수수료의 세부 기준은 미확인 항목입니다. 결제 전에 병원의 서면 조건을 받으세요. 예약 취소 요청, 취소 완료, 환불 완료 여부는 각각 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 오델린 피부과의원 (hospital_id=30)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 오델린 피부과의원 안내: 운영 시간 밖에도 앱 상담 채팅에 문의를 남길 수 있지만 다음 운영 시간부터 순서대로 확인합니다. 이 채팅은 실시간 의료 대응 창구가 아니며 접수 메시지가 의료진 확인 완료를 의미하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_030_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
