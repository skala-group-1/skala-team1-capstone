---
doc_id: SAMPLE_HOSPITAL_FAQ_001
title: "도담솔 성형외과·피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 1
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 도담솔 성형외과·피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·중국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 도담솔 성형외과·피부과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 도담솔 성형외과·피부과의원 안내: 첫 방문은 상담 전용으로 접수합니다. 시술을 원하면 대면 상담 뒤 별도의 일정 안내를 받습니다. 상담을 받았다는 이유만으로 시술 예약이 생성되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 도담솔 성형외과·피부과의원 안내: 예약 요청 전에 앱 상담 채팅으로 상담 의제를 정리할 수 있습니다. 질문을 한 번에 모아 보내면 접수 담당자가 방문 준비 사항을 안내합니다. 원격으로 치료 계획을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 도담솔 성형외과·피부과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 접수합니다. 상담 질문을 미리 적어 오면 접수 시 함께 전달할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 도담솔 성형외과·피부과의원 안내: 대면 상담 후 항목별 견적서를 요청할 수 있습니다. 시술비, 부가세 포함 여부, 별도로 청구되는 항목을 확인한 뒤 진행 여부를 결정합니다. 온라인 안내 가격은 확정 가격이 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 도담솔 성형외과·피부과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 도담솔 성형외과·피부과의원 안내: 동행인은 대기 공간을 이용할 수 있습니다. 상담실 동석을 원하면 방문 전에 앱 상담 채팅으로 요청하고 병원 확인을 받아야 합니다. 시술 공간에는 이 안내만으로 동행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 도담솔 성형외과·피부과의원 안내: 앱 상담 채팅에 기존 예약 정보와 변경 희망 날짜 2개를 보내 주세요. 병원이 가능한 일정을 안내한 뒤 기존 예약 처리와 새 예약 절차를 확인합니다. 메시지를 보낸 것만으로 날짜가 바뀌지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 도담솔 성형외과·피부과의원 안내: 귀국 최소 3영업일 전에 필요한 자료와 수령 희망일을 앱 상담 채팅으로 알려 주세요. 온라인 전달 가능 여부와 직접 수령 필요 여부를 구분해 안내하며 외국어 번역은 별도 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 도담솔 성형외과·피부과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 받고 담당자가 확인 후 연락 절차를 안내합니다. 문의를 보냈다는 이유만으로 후속 진료 예약이 생성되지는 않으며 별도 방문이 필요하면 일정을 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 도담솔 성형외과·피부과의원 안내: 첫 온라인 문의에는 사진을 첨부하지 않고 상담 내용을 텍스트로 보내 주세요. 필요한 자료는 담당자가 안내합니다. 방문 중 의료진이나 다른 방문객이 보이는 촬영은 허가 없이 진행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 도담솔 성형외과·피부과의원 안내: 방문 최소 2영업일 전에 앱 상담 채팅으로 사용하는 보조기기와 동행 여부를 알려 주세요. 건물 진입, 엘리베이터, 상담 공간의 이동 경로를 확인한 뒤 안내합니다. 접근 가능 여부는 확인 전까지 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 도담솔 성형외과·피부과의원 안내: 예약금 유무와 환불 비율은 이 안내만으로 확인할 수 없습니다. 예약 번호와 결제 여부를 알려 주고 본인 예약에 적용되는 취소 조건을 확인해야 합니다. 예약 취소 버튼을 눌렀다고 자동 환불된다고 안내하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 도담솔 성형외과·피부과의원 (hospital_id=1)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 도담솔 성형외과·피부과의원 안내: 앱 상담 채팅은 운영 시간 밖에 즉시 응답하는 서비스가 아닙니다. 담당자가 다음 운영 시간에 내용을 확인하며, 의료진의 실시간 상담이나 응급 대응을 제공하는 채널은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_001_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
