---
doc_id: SAMPLE_HOSPITAL_FAQ_027
title: "빛나래 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 27
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 빛나래 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다. 외국어 지원은 이 목록에서 확인되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 빛나래 성형외과의원 안내: 통역 지원을 제공합니다. 방문 1영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 빛나래 성형외과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 빛나래 성형외과의원 안내: 방문 전 상담 채팅에서 안내 자료를 요청할 수 있습니다. 상담 채팅은 필요한 자료와 방문 절차를 확인하는 용도이며, 담당 의사와의 실시간 온라인 진료는 제공하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 빛나래 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 10분 전에 접수합니다. 이전 상담 자료가 있다면 원본 파일 또는 사본을 지참할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 빛나래 성형외과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 빛나래 성형외과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 빛나래 성형외과의원 안내: 동행인은 대기 공간을 이용할 수 있습니다. 상담실 동석을 원하면 방문 전에 앱 상담 채팅으로 요청하고 병원 확인을 받아야 합니다. 시술 공간에는 이 안내만으로 동행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 빛나래 성형외과의원 안내: 앱 상담 채팅에 기존 예약 정보와 새 항공편에 맞춘 방문 가능 기간을 알려 주세요. 통역을 배정받았다면 새 일정에서 다시 확인합니다. 변경 요청 접수와 새 일정 확정은 서로 다른 단계입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 빛나래 성형외과의원 안내: 자료가 필요하면 귀국 최소 2영업일 전에 앱 상담 채팅으로 필요한 문서 종류와 언어를 알려 주세요. 발급 가능 여부, 본인 확인 방법, 수령 시점과 비용을 먼저 안내합니다. 모든 문서의 외국어 발급을 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 빛나래 성형외과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 빛나래 성형외과의원 안내: 본인이 상담받을 부위의 참고 사진은 담당자 안내에 따라 제출합니다. 여권 사본이나 결제 카드 사진을 일반 상담 자료로 보내지 마세요. 진료 공간 촬영은 현장 허가가 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 빛나래 성형외과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 빛나래 성형외과의원 안내: 항공편 변경이나 일정 취소에 따른 환불 가능 여부는 이 FAQ에 정의되어 있지 않습니다. 예약 정보와 결제 내역을 바탕으로 병원에 적용 조건을 확인합니다. 예외적인 전액 환불을 약속하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 빛나래 성형외과의원 (hospital_id=27)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 빛나래 성형외과의원 안내: 운영 시간 밖에도 앱 상담 채팅에 문의를 남길 수 있지만 다음 운영 시간부터 순서대로 확인합니다. 이 채팅은 실시간 의료 대응 창구가 아니며 접수 메시지가 의료진 확인 완료를 의미하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_027_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
