---
doc_id: SAMPLE_HOSPITAL_FAQ_005
title: "루미엘 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 5
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 루미엘 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 루미엘 피부과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 2영업일 전까지 예약 요청 내용에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 루미엘 피부과의원 안내: 상담만 받을 수 있으며 다른 병원의 상담을 함께 받아도 됩니다. 상담 종료 시 안내 내용을 요청할 수 있고, 시술을 결정한 뒤 새 일정으로 예약을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 루미엘 피부과의원 안내: 예약 요청 전에 앱 상담 채팅으로 상담 의제를 정리할 수 있습니다. 질문을 한 번에 모아 보내면 접수 담당자가 방문 준비 사항을 안내합니다. 원격으로 치료 계획을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 루미엘 피부과의원 안내: 첫 방문에는 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 20분 전에 도착합니다. 접수대에서 방문 목적과 통역 신청 여부를 먼저 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 루미엘 피부과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 루미엘 피부과의원 안내: 지각이 예상되면 예약 확인 메시지와 예상 도착 시각을 앱 상담 채팅에 보내 주세요. 도착 후 당일 상담 순서를 다시 안내하며 원래 예약 순서가 유지된다고 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 루미엘 피부과의원 안내: 기본 상담은 방문객 본인과 의료진이 진행합니다. 의사소통 지원을 위한 성인 동행인이 필요하면 예약 요청에 목적과 인원을 적어 사전 확인을 받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 루미엘 피부과의원 안내: 새로운 날짜가 필요하면 앱 상담 채팅에 기존 예약과 변경 사유를 남겨 주세요. 이용 가능한 시간은 업무 조회로 확인하고, 병원이 안내한 예약 변경 절차를 진행합니다. 동일 의료진 배정은 별도 확인 사항입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 루미엘 피부과의원 안내: 상담 요약과 진료 관련 자료는 서로 구분해 신청합니다. 필요한 문서의 용도, 희망 언어, 귀국 날짜를 전달하면 발급 범위와 비용을 안내합니다. 일반 상담 채팅 답변이 공식 진료 문서를 대신하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 루미엘 피부과의원 안내: 귀국 후 연락 방법은 마지막 방문 때 안내받을 수 있으며 기본 접수 창구는 앱 상담 채팅입니다. 문의 시 방문 날짜와 연락 가능한 시간을 적어 주세요. 추가 대면 확인이 필요한지는 의료진이 판단합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 루미엘 피부과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 루미엘 피부과의원 안내: 동행인과 함께 방문하는지, 계단 이용이 가능한지, 어떤 보조기기를 사용하는지 예약 요청에 적어 주세요. 이동 경로를 확인한 답변을 받은 뒤 방문 계획을 확정합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 루미엘 피부과의원 안내: 예약금 유무와 환불 비율은 이 안내만으로 확인할 수 없습니다. 예약 번호와 결제 여부를 알려 주고 본인 예약에 적용되는 취소 조건을 확인해야 합니다. 예약 취소 버튼을 눌렀다고 자동 환불된다고 안내하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 루미엘 피부과의원 (hospital_id=5)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 루미엘 피부과의원 안내: 야간이나 휴무일의 채팅은 접수만 가능하고 담당자 답변은 다음 운영 시간에 진행합니다. 답변 시각을 확정적으로 보장하지 않으며 급한 의료 상황의 대응 수단으로 사용하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_005_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
