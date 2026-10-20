---
doc_id: SAMPLE_HOSPITAL_FAQ_010
title: "하늘결 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 10
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 하늘결 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 하늘결 피부과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 2영업일 전까지 앱 상담 채팅에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 하늘결 피부과의원 안내: 상담만 방문할 수 있습니다. 예약 요청의 상담 내용에 상담만 희망한다고 적어 주세요. 시술 일정은 상담 종료 후 별도로 요청하며 당일 시술은 의무가 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 하늘결 피부과의원 안내: 방문 전에는 앱 상담 채팅으로 질문 목록과 방문 희망 기간을 접수합니다. 사진 자료는 담당자가 요청했을 때 전달합니다. 별도 화상 상담은 운영하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 하늘결 피부과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 접수합니다. 상담 질문을 미리 적어 오면 접수 시 함께 전달할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 하늘결 피부과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 하늘결 피부과의원 안내: 예약 시각을 넘길 것 같으면 앱 상담 채팅으로 먼저 연락해 주세요. 20분 이상 늦는 경우 당일 상담 가능 여부를 다시 확인하며, 가능한 시간이 없으면 다른 일정을 안내합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 하늘결 피부과의원 안내: 성인 동행인 최대 2명의 대기 공간 이용이 가능합니다. 상담실 동석은 1명까지 사전 요청할 수 있으며, 별도 통역 동행도 인원에 포함됩니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 하늘결 피부과의원 안내: 새로운 날짜가 필요하면 앱 상담 채팅에 기존 예약과 변경 사유를 남겨 주세요. 이용 가능한 시간은 업무 조회로 확인하고, 병원이 안내한 예약 변경 절차를 진행합니다. 동일 의료진 배정은 별도 확인 사항입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 하늘결 피부과의원 안내: 다음 방문에서 자료를 받으려면 방문 최소 2영업일 전에 앱 상담 채팅으로 문서 종류를 알려 주세요. 본인 확인, 발급 비용, 준비 여부를 안내받아야 하며 대리 수령은 별도 확인이 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 하늘결 피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 하늘결 피부과의원 안내: 사전 사진은 담당자가 요청한 자료만 전달합니다. 다른 사람의 얼굴이나 개인정보가 보이는 사진은 보내지 마세요. 상담실 촬영과 녹음은 시작 전에 의료진과 동석자의 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 하늘결 피부과의원 안내: 방문 최소 3영업일 전에 앱 상담 채팅으로 이동 지원이 필요한 구간을 알려 주세요. 건물 입구부터 접수 공간까지 확인한 후 안내하며 확인되지 않은 시설을 이용 가능하다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 하늘결 피부과의원 안내: 이 FAQ는 개별 예약의 환불 조건을 포함하지 않습니다. 결제 전 취소 가능한 시점, 환불 금액의 계산 기준, 처리 방법을 문서로 요청해 주세요. 정확한 금액은 해당 예약의 결제 조건을 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 하늘결 피부과의원 (hospital_id=10)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 하늘결 피부과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_010_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
