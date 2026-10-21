---
doc_id: SAMPLE_HOSPITAL_FAQ_016
title: "리안솔 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 16
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 리안솔 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 리안솔 피부과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 리안솔 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 리안솔 피부과의원 안내: 온라인 사전 문의는 텍스트 상담으로 받습니다. 관심 부위, 이전 상담 여부, 한국 체류 기간을 적어 주세요. 의료진의 대면 진찰을 대신하는 진료 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 리안솔 피부과의원 안내: 첫 방문은 예약 시각 20분 전부터 접수합니다. 예약 확인 메시지와 신분 확인용 여권을 준비하고, 동행인이 있다면 접수대에 함께 도착했다고 알려 주세요.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 리안솔 피부과의원 안내: 온라인 견적과 실제 결제 금액은 상담 결과에 따라 달라질 수 있습니다. 두 가지 이상을 상담한 경우 항목별 견적과 함께 진행하는 견적을 구분해 요청할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 리안솔 피부과의원 안내: 지각이 예상되면 예약 확인 메시지와 예상 도착 시각을 앱 상담 채팅에 보내 주세요. 도착 후 당일 상담 순서를 다시 안내하며 원래 예약 순서가 유지된다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 리안솔 피부과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 리안솔 피부과의원 안내: 방문 날짜 변경은 기존 예약 정보를 첨부해 앱 상담 채팅으로 문의합니다. 병원이 가능한 날짜를 안내한 뒤 필요한 취소 및 재예약 절차를 확인합니다. 새 요청만으로 기존 예약이 자동 취소되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 리안솔 피부과의원 안내: 상담 요약과 진료 관련 자료는 서로 구분해 신청합니다. 필요한 문서의 용도, 희망 언어, 귀국 날짜를 전달하면 발급 범위와 비용을 안내합니다. 일반 상담 채팅 답변이 공식 진료 문서를 대신하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 리안솔 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 리안솔 피부과의원 안내: 본인이 상담받을 부위의 참고 사진은 담당자 안내에 따라 제출합니다. 여권 사본이나 결제 카드 사진을 일반 상담 자료로 보내지 마세요. 진료 공간 촬영은 현장 허가가 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 리안솔 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 리안솔 피부과의원 안내: 이 FAQ에는 예약금 금액과 취소 시점별 환불 기준이 등록되어 있지 않습니다. 결제 전 앱 상담 채팅으로 예약금 유무와 환불 조건을 서면으로 요청해 주세요. 앱의 예약 취소와 결제 금액 환불 처리는 같은 절차로 단정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 리안솔 피부과의원 (hospital_id=16)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 리안솔 피부과의원 안내: 운영 시간 밖에 남긴 문의는 다음 운영 시간에 담당자가 확인합니다. 예약 관련 문의에는 예약 번호와 희망 연락 시간을 함께 남겨 주세요. 자동 접수 안내와 실제 답변은 구분해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_016_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
