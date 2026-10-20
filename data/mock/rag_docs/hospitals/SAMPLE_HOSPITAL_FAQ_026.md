---
doc_id: SAMPLE_HOSPITAL_FAQ_026
title: "청아린 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 26
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 청아린 피부과의원 (hospital_id=26)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 청아린 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·중국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 청아린 피부과의원 (hospital_id=26)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 청아린 피부과의원 안내: 통역 지원을 제공합니다. 방문 3영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 청아린 피부과의원 (hospital_id=26)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 청아린 피부과의원 안내: 상담만 받는 방문과 시술을 함께 희망하는 방문을 구분해 접수합니다. 예약 요청 시 원하는 방문 유형을 알려 주세요. 시술을 희망해도 당일 진행이 확정되는 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 청아린 피부과의원 (hospital_id=26)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 청아린 피부과의원 안내: 방문 전 상담 채팅에서 안내 자료를 요청할 수 있습니다. 상담 채팅은 필요한 자료와 방문 절차를 확인하는 용도이며, 담당 의사와의 실시간 온라인 진료는 제공하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 청아린 피부과의원 (hospital_id=26)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 청아린 피부과의원 안내: 첫 방문은 예약 시각 20분 전부터 접수합니다. 예약 확인 메시지와 신분 확인용 여권을 준비하고, 동행인이 있다면 접수대에 함께 도착했다고 알려 주세요.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 청아린 피부과의원 (hospital_id=26)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 청아린 피부과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 청아린 피부과의원 (hospital_id=26)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 청아린 피부과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 청아린 피부과의원 (hospital_id=26)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 청아린 피부과의원 안내: 상담실에는 성인 동행인 1명까지 함께 들어갈 수 있습니다. 예약 요청에 동행 여부를 적어 주세요. 검사나 처치 공간의 동행 가능 여부는 별도로 안내하며 상담실 기준과 같지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 청아린 피부과의원 (hospital_id=26)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 청아린 피부과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 청아린 피부과의원 (hospital_id=26)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 청아린 피부과의원 안내: 다음 방문에서 자료를 받으려면 방문 최소 2영업일 전에 앱 상담 채팅으로 문서 종류를 알려 주세요. 본인 확인, 발급 비용, 준비 여부를 안내받아야 하며 대리 수령은 별도 확인이 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 청아린 피부과의원 (hospital_id=26)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 청아린 피부과의원 안내: 귀국 이후에는 앱 상담 채팅에 예약 정보와 질문을 남겨 주세요. 필요한 사진은 담당자가 요청한 경우에 전달합니다. 답변은 후속 상담 절차 안내이며 채팅으로 진단을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 청아린 피부과의원 (hospital_id=26)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 청아린 피부과의원 안내: 본인이 상담받을 부위의 참고 사진은 담당자 안내에 따라 제출합니다. 여권 사본이나 결제 카드 사진을 일반 상담 자료로 보내지 마세요. 진료 공간 촬영은 현장 허가가 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 청아린 피부과의원 (hospital_id=26)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 청아린 피부과의원 안내: 방문 최소 2영업일 전에 앱 상담 채팅으로 사용하는 보조기기와 동행 여부를 알려 주세요. 건물 진입, 엘리베이터, 상담 공간의 이동 경로를 확인한 뒤 안내합니다. 접근 가능 여부는 확인 전까지 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 청아린 피부과의원 (hospital_id=26)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 청아린 피부과의원 안내: 이 FAQ는 개별 예약의 환불 조건을 포함하지 않습니다. 결제 전 취소 가능한 시점, 환불 금액의 계산 기준, 처리 방법을 문서로 요청해 주세요. 정확한 금액은 해당 예약의 결제 조건을 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 청아린 피부과의원 (hospital_id=26)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 청아린 피부과의원 안내: 휴무일에도 문의 내용을 남길 수 있으나 답변은 병원 운영 시간에 진행합니다. 변경할 예약이 임박했다면 해당 사실을 메시지에 적어 주세요. 읽음 표시만으로 예약 변경이나 의료진 검토가 완료된 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_026_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
