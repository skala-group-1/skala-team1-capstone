---
doc_id: SAMPLE_HOSPITAL_FAQ_050
title: "다온결 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 50
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 다온결 피부과의원 (hospital_id=50)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 다온결 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 다온결 피부과의원 (hospital_id=50)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 다온결 피부과의원 안내: 통역 지원을 제공합니다. 방문 5영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 다온결 피부과의원 (hospital_id=50)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 다온결 피부과의원 안내: 상담만 받는 방문과 시술을 함께 희망하는 방문을 구분해 접수합니다. 예약 요청 시 원하는 방문 유형을 알려 주세요. 시술을 희망해도 당일 진행이 확정되는 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 다온결 피부과의원 (hospital_id=50)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 다온결 피부과의원 안내: 온라인 사전 문의는 텍스트 상담으로 받습니다. 관심 부위, 이전 상담 여부, 한국 체류 기간을 적어 주세요. 의료진의 대면 진찰을 대신하는 진료 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 다온결 피부과의원 (hospital_id=50)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 다온결 피부과의원 안내: 첫 방문은 예약 시각 20분 전부터 접수합니다. 예약 확인 메시지와 신분 확인용 여권을 준비하고, 동행인이 있다면 접수대에 함께 도착했다고 알려 주세요.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 다온결 피부과의원 (hospital_id=50)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 다온결 피부과의원 안내: 온라인 견적은 확정 금액이 아닙니다. 대면 상담 후 시술 항목, 부가세 포함 여부, 약제비와 후속 방문 비용을 구분한 견적을 요청할 수 있습니다. 항목이 변경되면 다시 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 다온결 피부과의원 (hospital_id=50)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 다온결 피부과의원 안내: 예약 시각보다 15분 이상 늦으면 접수 담당자가 당일 상담 가능 여부를 다시 확인합니다. 지각이 예상될 때는 앱 상담 채팅에 먼저 알려 주세요. 가능한 시간이 없으면 일정 변경을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 다온결 피부과의원 (hospital_id=50)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 다온결 피부과의원 안내: 동행인은 대기 공간을 이용할 수 있습니다. 상담실 동석을 원하면 방문 전에 앱 상담 채팅으로 요청하고 병원 확인을 받아야 합니다. 시술 공간에는 이 안내만으로 동행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 다온결 피부과의원 (hospital_id=50)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 다온결 피부과의원 안내: 앱 상담 채팅에 기존 예약 정보와 새 항공편에 맞춘 방문 가능 기간을 알려 주세요. 통역을 배정받았다면 새 일정에서 다시 확인합니다. 변경 요청 접수와 새 일정 확정은 서로 다른 단계입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 다온결 피부과의원 (hospital_id=50)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 다온결 피부과의원 안내: 귀국 최소 3영업일 전에 필요한 자료와 수령 희망일을 앱 상담 채팅으로 알려 주세요. 온라인 전달 가능 여부와 직접 수령 필요 여부를 구분해 안내하며 외국어 번역은 별도 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 다온결 피부과의원 (hospital_id=50)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 다온결 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 다온결 피부과의원 (hospital_id=50)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 다온결 피부과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 다온결 피부과의원 (hospital_id=50)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 다온결 피부과의원 안내: 예약 요청 시 계단 이용의 어려움과 필요한 이동 지원을 적어 주세요. 접수 담당자가 이동 경로와 동행 필요 사항을 확인해 안내합니다. 별도 이동 보조 인력 제공은 확정된 서비스가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 다온결 피부과의원 (hospital_id=50)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 다온결 피부과의원 안내: 이 FAQ에는 예약금 금액과 취소 시점별 환불 기준이 등록되어 있지 않습니다. 결제 전 앱 상담 채팅으로 예약금 유무와 환불 조건을 서면으로 요청해 주세요. 앱의 예약 취소와 결제 금액 환불 처리는 같은 절차로 단정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 다온결 피부과의원 (hospital_id=50)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 다온결 피부과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_050_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
