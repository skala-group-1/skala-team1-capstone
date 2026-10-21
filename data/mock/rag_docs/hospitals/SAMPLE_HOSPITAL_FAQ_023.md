---
doc_id: SAMPLE_HOSPITAL_FAQ_023
title: "가온누리 피부과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 23
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 가온누리 피부과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·영어·일본어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 가온누리 피부과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 5영업일 전까지 앱 상담 채팅에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 가온누리 피부과의원 안내: 상담만 받을 수 있으며 다른 병원의 상담을 함께 받아도 됩니다. 상담 종료 시 안내 내용을 요청할 수 있고, 시술을 결정한 뒤 새 일정으로 예약을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 가온누리 피부과의원 안내: 온라인 사전 문의는 텍스트 상담으로 받습니다. 관심 부위, 이전 상담 여부, 한국 체류 기간을 적어 주세요. 의료진의 대면 진찰을 대신하는 진료 서비스는 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 가온누리 피부과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 방문합니다. 복용 중인 약과 이전 시술 이력을 정리한 메모가 있다면 상담 시 의료진에게 전달합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 가온누리 피부과의원 안내: 온라인 견적에는 견적 대상 시술과 포함 항목을 함께 안내합니다. 대면 상담에서 계획이 바뀌면 새 견적을 확인해야 하며, 기존 안내만으로 최종 결제 금액이 확정되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 가온누리 피부과의원 안내: 예약 시각보다 15분 이상 늦으면 접수 담당자가 당일 상담 가능 여부를 다시 확인합니다. 지각이 예상될 때는 앱 상담 채팅에 먼저 알려 주세요. 가능한 시간이 없으면 일정 변경을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 가온누리 피부과의원 안내: 상담실에는 성인 동행인 1명까지 함께 들어갈 수 있습니다. 예약 요청에 동행 여부를 적어 주세요. 검사나 처치 공간의 동행 가능 여부는 별도로 안내하며 상담실 기준과 같지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 가온누리 피부과의원 안내: 방문 날짜 변경은 기존 예약 정보를 첨부해 앱 상담 채팅으로 문의합니다. 병원이 가능한 날짜를 안내한 뒤 필요한 취소 및 재예약 절차를 확인합니다. 새 요청만으로 기존 예약이 자동 취소되지는 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 가온누리 피부과의원 안내: 다음 방문에서 자료를 받으려면 방문 최소 2영업일 전에 앱 상담 채팅으로 문서 종류를 알려 주세요. 본인 확인, 발급 비용, 준비 여부를 안내받아야 하며 대리 수령은 별도 확인이 필요합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 가온누리 피부과의원 안내: 귀국 이후에는 앱 상담 채팅에 예약 정보와 질문을 남겨 주세요. 필요한 사진은 담당자가 요청한 경우에 전달합니다. 답변은 후속 상담 절차 안내이며 채팅으로 진단을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 가온누리 피부과의원 안내: 첫 온라인 문의에는 사진을 첨부하지 않고 상담 내용을 텍스트로 보내 주세요. 필요한 자료는 담당자가 안내합니다. 방문 중 의료진이나 다른 방문객이 보이는 촬영은 허가 없이 진행할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 가온누리 피부과의원 안내: 동행인과 함께 방문하는지, 계단 이용이 가능한지, 어떤 보조기기를 사용하는지 예약 요청에 적어 주세요. 이동 경로를 확인한 답변을 받은 뒤 방문 계획을 확정합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 가온누리 피부과의원 안내: 항공편 변경이나 일정 취소에 따른 환불 가능 여부는 이 FAQ에 정의되어 있지 않습니다. 예약 정보와 결제 내역을 바탕으로 병원에 적용 조건을 확인합니다. 예외적인 전액 환불을 약속하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 가온누리 피부과의원 (hospital_id=23)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 가온누리 피부과의원 안내: 휴무일에도 문의 내용을 남길 수 있으나 답변은 병원 운영 시간에 진행합니다. 변경할 예약이 임박했다면 해당 사실을 메시지에 적어 주세요. 읽음 표시만으로 예약 변경이나 의료진 검토가 완료된 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_023_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
