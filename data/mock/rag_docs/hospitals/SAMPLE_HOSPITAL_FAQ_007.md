---
doc_id: SAMPLE_HOSPITAL_FAQ_007
title: "해솔린 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 7
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 해솔린 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·중국어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 해솔린 성형외과의원 안내: 통역 지원을 제공합니다. 방문 2영업일 전까지 앱 상담 채팅에 희망 언어, 예약 정보, 통역이 필요한 상담 범위를 전달해 신청합니다. 병원이 해당 언어의 배정 가능 여부, 제공 범위와 비용을 안내한 뒤 확정합니다. 지원 언어 목록을 통역 가능 언어 목록으로 간주하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 해솔린 성형외과의원 안내: 상담만 받는 방문과 시술을 함께 희망하는 방문을 구분해 접수합니다. 예약 요청 시 원하는 방문 유형을 알려 주세요. 시술을 희망해도 당일 진행이 확정되는 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 해솔린 성형외과의원 안내: 방문 전 앱 상담 채팅으로 관심 시술과 질문을 전달할 수 있습니다. 답변은 방문 준비와 상담 절차 안내이며 사진만으로 진단하거나 시술 가능 여부를 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 해솔린 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 10분 전에 접수합니다. 이전 상담 자료가 있다면 원본 파일 또는 사본을 지참할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 해솔린 성형외과의원 안내: 온라인 견적에는 견적 대상 시술과 포함 항목을 함께 안내합니다. 대면 상담에서 계획이 바뀌면 새 견적을 확인해야 하며, 기존 안내만으로 최종 결제 금액이 확정되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 해솔린 성형외과의원 안내: 지각이 예상되면 예약 확인 메시지와 예상 도착 시각을 앱 상담 채팅에 보내 주세요. 도착 후 당일 상담 순서를 다시 안내하며 원래 예약 순서가 유지된다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 해솔린 성형외과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 해솔린 성형외과의원 안내: 앱 상담 채팅에 기존 예약 정보와 새 항공편에 맞춘 방문 가능 기간을 알려 주세요. 통역을 배정받았다면 새 일정에서 다시 확인합니다. 변경 요청 접수와 새 일정 확정은 서로 다른 단계입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 해솔린 성형외과의원 안내: 다음 방문에서 자료를 받으려면 방문 최소 2영업일 전에 앱 상담 채팅으로 문서 종류를 알려 주세요. 본인 확인, 발급 비용, 준비 여부를 안내받아야 하며 대리 수령은 별도 확인이 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 해솔린 성형외과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 해솔린 성형외과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 해솔린 성형외과의원 안내: 동행인과 함께 방문하는지, 계단 이용이 가능한지, 어떤 보조기기를 사용하는지 예약 요청에 적어 주세요. 이동 경로를 확인한 답변을 받은 뒤 방문 계획을 확정합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 해솔린 성형외과의원 안내: 이 FAQ는 개별 예약의 환불 조건을 포함하지 않습니다. 결제 전 취소 가능한 시점, 환불 금액의 계산 기준, 처리 방법을 문서로 요청해 주세요. 정확한 금액은 해당 예약의 결제 조건을 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 해솔린 성형외과의원 (hospital_id=7)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 해솔린 성형외과의원 안내: 야간이나 휴무일의 채팅은 접수만 가능하고 담당자 답변은 다음 운영 시간에 진행합니다. 답변 시각을 확정적으로 보장하지 않으며 급한 의료 상황의 대응 수단으로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_007_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
