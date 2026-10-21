---
doc_id: SAMPLE_HOSPITAL_FAQ_032
title: "로하엘 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 32
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 로하엘 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 로하엘 성형외과의원 안내: 통역 지원을 제공합니다. 방문 5영업일 전까지 예약 요청 내용에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 로하엘 성형외과의원 안내: 첫 방문은 상담 전용으로 접수합니다. 시술을 원하면 대면 상담 뒤 별도의 일정 안내를 받습니다. 상담을 받았다는 이유만으로 시술 예약이 생성되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 로하엘 성형외과의원 안내: 예약 요청 전에 앱 상담 채팅으로 상담 의제를 정리할 수 있습니다. 질문을 한 번에 모아 보내면 접수 담당자가 방문 준비 사항을 안내합니다. 원격으로 치료 계획을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 로하엘 성형외과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 접수합니다. 상담 질문을 미리 적어 오면 접수 시 함께 전달할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 로하엘 성형외과의원 안내: 온라인 견적에는 견적 대상 시술과 포함 항목을 함께 안내합니다. 대면 상담에서 계획이 바뀌면 새 견적을 확인해야 하며, 기존 안내만으로 최종 결제 금액이 확정되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 로하엘 성형외과의원 안내: 늦는 경우 앱 상담 채팅으로 도착 예정 시각을 알려 주세요. 통역을 신청했다면 통역 배정 시간도 함께 재확인합니다. 변경된 방문 시각은 병원의 안내를 받은 뒤 확정합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 로하엘 성형외과의원 안내: 상담실에는 성인 동행인 1명까지 함께 들어갈 수 있습니다. 예약 요청에 동행 여부를 적어 주세요. 검사나 처치 공간의 동행 가능 여부는 별도로 안내하며 상담실 기준과 같지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 로하엘 성형외과의원 안내: 일정 변경은 앱 상담 채팅에서 요청합니다. 기존 예약 시각, 새 방문 희망 기간, 통역 신청 여부를 함께 알려 주세요. 병원의 변경 안내 전까지 기존 예약이 변경된 것으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 로하엘 성형외과의원 안내: 자료 발급은 방문 당일 접수대 또는 앱 상담 채팅에서 신청합니다. 문서 종류에 따라 준비 기간이 다르므로 귀국 일정을 함께 전달해 주세요. 본인 확인과 비용 안내를 받은 후 수령 절차를 진행합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 로하엘 성형외과의원 안내: 귀국 후 연락 방법은 마지막 방문 때 안내받을 수 있으며 기본 접수 창구는 앱 상담 채팅입니다. 문의 시 방문 날짜와 연락 가능한 시간을 적어 주세요. 추가 대면 확인이 필요한지는 의료진이 판단합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 로하엘 성형외과의원 안내: 기존 상담 자료나 참고 사진은 방문 시 보여 줄 수 있습니다. 온라인 제출이 필요하면 먼저 담당자에게 전달 방법을 확인합니다. 참고 사진은 동일 결과를 보장하는 자료로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 로하엘 성형외과의원 안내: 방문 최소 2영업일 전에 앱 상담 채팅으로 사용하는 보조기기와 동행 여부를 알려 주세요. 건물 진입, 엘리베이터, 상담 공간의 이동 경로를 확인한 뒤 안내합니다. 접근 가능 여부는 확인 전까지 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 로하엘 성형외과의원 안내: 예약금과 취소 수수료의 세부 기준은 미확인 항목입니다. 결제 전에 병원의 서면 조건을 받으세요. 예약 취소 요청, 취소 완료, 환불 완료 여부는 각각 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 로하엘 성형외과의원 (hospital_id=32)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 로하엘 성형외과의원 안내: 야간이나 휴무일의 채팅은 접수만 가능하고 담당자 답변은 다음 운영 시간에 진행합니다. 답변 시각을 확정적으로 보장하지 않으며 급한 의료 상황의 대응 수단으로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_032_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
