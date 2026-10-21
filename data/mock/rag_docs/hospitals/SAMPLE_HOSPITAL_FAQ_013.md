---
doc_id: SAMPLE_HOSPITAL_FAQ_013
title: "담율 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 13
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 담율 피부과의원 (hospital_id=13)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 담율 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 담율 피부과의원 (hospital_id=13)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 담율 피부과의원 안내: 통역 지원을 제공합니다. 방문 2영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 담율 피부과의원 (hospital_id=13)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 담율 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 담율 피부과의원 (hospital_id=13)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 담율 피부과의원 안내: 방문 전 앱 상담 채팅으로 관심 시술과 질문을 전달할 수 있습니다. 답변은 방문 준비와 상담 절차 안내이며 사진만으로 진단하거나 시술 가능 여부를 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 담율 피부과의원 (hospital_id=13)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 담율 피부과의원 안내: 첫 방문은 예약 시각 20분 전부터 접수합니다. 예약 확인 메시지와 신분 확인용 여권을 준비하고, 동행인이 있다면 접수대에 함께 도착했다고 알려 주세요.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 담율 피부과의원 (hospital_id=13)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 담율 피부과의원 안내: 온라인 견적과 실제 결제 금액은 상담 결과에 따라 달라질 수 있습니다. 두 가지 이상을 상담한 경우 항목별 견적과 함께 진행하는 견적을 구분해 요청할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 담율 피부과의원 (hospital_id=13)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 담율 피부과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 담율 피부과의원 (hospital_id=13)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 담율 피부과의원 안내: 상담실에는 성인 동행인 1명까지 함께 들어갈 수 있습니다. 예약 요청에 동행 여부를 적어 주세요. 검사나 처치 공간의 동행 가능 여부는 별도로 안내하며 상담실 기준과 같지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 담율 피부과의원 (hospital_id=13)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 담율 피부과의원 안내: 앱 상담 채팅에 기존 예약 정보와 변경 희망 날짜 2개를 보내 주세요. 병원이 가능한 일정을 안내한 뒤 기존 예약 처리와 새 예약 절차를 확인합니다. 메시지를 보낸 것만으로 날짜가 바뀌지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 담율 피부과의원 (hospital_id=13)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 담율 피부과의원 안내: 다음 방문에서 자료를 받으려면 방문 최소 2영업일 전에 앱 상담 채팅으로 문서 종류를 알려 주세요. 본인 확인, 발급 비용, 준비 여부를 안내받아야 하며 대리 수령은 별도 확인이 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 담율 피부과의원 (hospital_id=13)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 담율 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 담율 피부과의원 (hospital_id=13)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 담율 피부과의원 안내: 첫 온라인 문의에는 사진을 첨부하지 않고 상담 내용을 텍스트로 보내 주세요. 필요한 자료는 담당자가 안내합니다. 방문 중 의료진이나 다른 방문객이 보이는 촬영은 허가 없이 진행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 담율 피부과의원 (hospital_id=13)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 담율 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 담율 피부과의원 (hospital_id=13)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 담율 피부과의원 안내: 예약금과 취소 수수료의 세부 기준은 미확인 항목입니다. 결제 전에 병원의 서면 조건을 받으세요. 예약 취소 요청, 취소 완료, 환불 완료 여부는 각각 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 담율 피부과의원 (hospital_id=13)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 담율 피부과의원 안내: 운영 시간 밖에 남긴 문의는 다음 운영 시간에 담당자가 확인합니다. 예약 관련 문의에는 예약 번호와 희망 연락 시간을 함께 남겨 주세요. 자동 접수 안내와 실제 답변은 구분해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_013_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
