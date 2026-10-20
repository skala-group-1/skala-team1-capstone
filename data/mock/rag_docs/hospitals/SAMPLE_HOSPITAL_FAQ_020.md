---
doc_id: SAMPLE_HOSPITAL_FAQ_020
title: "솔빛담 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 20
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 솔빛담 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어·중국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 솔빛담 성형외과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 5영업일 전까지 앱 상담 채팅에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 솔빛담 성형외과의원 안내: 상담만 받는 일정을 먼저 요청할 수 있습니다. 두 가지 이상의 고민을 상담하려면 예약 요청에 모두 적어 주세요. 실제 상담 범위와 추가 방문 필요 여부는 병원이 확인해 안내합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 솔빛담 성형외과의원 안내: 방문 전 앱 상담 채팅으로 관심 시술과 질문을 전달할 수 있습니다. 답변은 방문 준비와 상담 절차 안내이며 사진만으로 진단하거나 시술 가능 여부를 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 솔빛담 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 10분 전에 접수합니다. 이전 상담 자료가 있다면 원본 파일 또는 사본을 지참할 수 있습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 솔빛담 성형외과의원 안내: 온라인에서 안내한 금액은 상담 전 참고 견적입니다. 대면 상담 뒤 기본 항목과 선택 항목을 나눠 확인하고, 추가 항목을 선택하기 전에 변경 금액을 안내받습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 솔빛담 성형외과의원 안내: 예약 시각보다 15분 이상 늦으면 접수 담당자가 당일 상담 가능 여부를 다시 확인합니다. 지각이 예상될 때는 앱 상담 채팅에 먼저 알려 주세요. 가능한 시간이 없으면 일정 변경을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 솔빛담 성형외과의원 안내: 성인 동행인 최대 2명의 대기 공간 이용이 가능합니다. 상담실 동석은 1명까지 사전 요청할 수 있으며, 별도 통역 동행도 인원에 포함됩니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 솔빛담 성형외과의원 안내: 새로운 날짜가 필요하면 앱 상담 채팅에 기존 예약과 변경 사유를 남겨 주세요. 이용 가능한 시간은 업무 조회로 확인하고, 병원이 안내한 예약 변경 절차를 진행합니다. 동일 의료진 배정은 별도 확인 사항입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 솔빛담 성형외과의원 안내: 자료 발급은 방문 당일 접수대 또는 앱 상담 채팅에서 신청합니다. 문서 종류에 따라 준비 기간이 다르므로 귀국 일정을 함께 전달해 주세요. 본인 확인과 비용 안내를 받은 후 수령 절차를 진행합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 솔빛담 성형외과의원 안내: 귀국 후 문의는 앱 상담 채팅으로 접수합니다. 한국과의 시차, 연락 가능한 시간, 방문 날짜를 함께 적어 주세요. 실시간 의료진 응답이나 해외 원격 진료를 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 솔빛담 성형외과의원 안내: 사전 자료는 상담 채팅에서 담당자가 요청했을 때 전달합니다. 상담 내용을 기록하고 싶으면 메모를 요청할 수 있으며 사진 촬영과 녹음은 별도 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 솔빛담 성형외과의원 안내: 방문 전 앱 상담 채팅에 보조기기 종류와 이동 시 필요한 도움을 알려 주세요. 예약 시각에 맞춰 접수 동선을 안내하며 실제 접근 가능 여부는 시설 확인 후 답변합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 솔빛담 성형외과의원 안내: 예약금 유무와 환불 비율은 이 안내만으로 확인할 수 없습니다. 예약 번호와 결제 여부를 알려 주고 본인 예약에 적용되는 취소 조건을 확인해야 합니다. 예약 취소 버튼을 눌렀다고 자동 환불된다고 안내하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 솔빛담 성형외과의원 (hospital_id=20)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 솔빛담 성형외과의원 안내: 운영 시간 밖에도 앱 상담 채팅에 문의를 남길 수 있지만 다음 운영 시간부터 순서대로 확인합니다. 이 채팅은 실시간 의료 대응 창구가 아니며 접수 메시지가 의료진 확인 완료를 의미하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_020_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
