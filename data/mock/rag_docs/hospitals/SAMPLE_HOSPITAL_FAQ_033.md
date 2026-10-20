---
doc_id: SAMPLE_HOSPITAL_FAQ_033
title: "엘린담 성형외과의원 — 방문·상담 FAQ"
doc_type: HOSPITAL_FAQ
hospital_id: 33
lang: ko
source: "SKALA capstone fictional dataset"
version: 1
is_synthetic: true
source_file: faq_samples/faq.jsonl
---

> Fictional educational content. Not medical advice.

가상 운영 정책입니다. 병원의 실제 승인·의료 검토를 받은 지침이 아닙니다.

## language

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 한국어를 못하는데 어떤 언어로 상담할 수 있나요?
답변: 엘린담 성형외과의원 안내: 상담 지원 언어로 등록된 언어는 한국어입니다. 지원 언어 목록만으로 해당 언어의 전담 통역 배정이나 특정 날짜의 이용 가능 여부를 확정할 수 없습니다. 외국어 지원은 이 목록에서 확인되지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_LANGUAGE
source_origin: existing_mock
status: existing_mock_fact

## interpreter

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 통역은 어떻게 신청하고 언제까지 알려야 하나요?
답변: 엘린담 성형외과의원 안내: 전담 통역 지원은 제공하지 않습니다. 외부 통역사나 의사소통을 돕는 동행인을 데려오려면 방문 5영업일 전까지 예약 요청 내용에 동행 여부와 희망 언어를 전달해 출입 가능 범위를 확인합니다. 앱 채팅 번역이 현장 통역을 제공하는 것은 아닙니다. 외부 통역의 비용 부담 조건은 별도로 확인해야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_INTERPRETER
source_origin: existing_mock_and_authored_synthetic
status: synthetic_draft

## consultation-only

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 상담만 받고 시술 여부는 나중에 결정해도 되나요?
답변: 엘린담 성형외과의원 안내: 상담만 받을 수 있으며 다른 병원의 상담을 함께 받아도 됩니다. 상담 종료 시 안내 내용을 요청할 수 있고, 시술을 결정한 뒤 새 일정으로 예약을 요청합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_CONSULTATION_ONLY
source_origin: authored_synthetic
status: synthetic_draft

## preconsultation

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 한국에 가기 전에 온라인으로 미리 상담할 수 있나요?
답변: 엘린담 성형외과의원 안내: 방문 전에는 앱 상담 채팅으로 질문 목록과 방문 희망 기간을 접수합니다. 사진 자료는 담당자가 요청했을 때 전달합니다. 별도 화상 상담은 운영하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_PRECONSULTATION
source_origin: authored_synthetic
status: synthetic_draft

## first-visit

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 처음 방문할 때 무엇을 준비하고 언제 도착하면 되나요?
답변: 엘린담 성형외과의원 안내: 예약 확인 메시지와 신분 확인용 여권을 준비하고 예약 시각 15분 전에 방문합니다. 복용 중인 약과 이전 시술 이력을 정리한 메모가 있다면 상담 시 의료진에게 전달합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_FIRST_VISIT
source_origin: authored_synthetic
status: synthetic_draft

## quote-scope

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 온라인에서 안내받은 견적이 최종 결제 금액인가요?
답변: 엘린담 성형외과의원 안내: 온라인 견적은 확정 금액이 아닙니다. 대면 상담 후 시술 항목, 부가세 포함 여부, 약제비와 후속 방문 비용을 구분한 견적을 요청할 수 있습니다. 항목이 변경되면 다시 확인합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_QUOTE_SCOPE
source_origin: authored_synthetic
status: synthetic_draft

## late-arrival

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 예약 시간에 늦을 것 같으면 어떻게 해야 하나요?
답변: 엘린담 성형외과의원 안내: 늦을 것으로 예상되면 앱 상담 채팅에 예약 시각과 예상 도착 시각을 남겨 주세요. 10분 이상 지각하면 남은 상담 시간을 확인하고 일정 재조정을 안내할 수 있습니다. 기존 예약의 자동 연장은 보장하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_LATE_ARRIVAL
source_origin: authored_synthetic
status: synthetic_draft

## companion

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 친구나 가족이 상담에 같이 들어가도 되나요?
답변: 엘린담 성형외과의원 안내: 상담실 동석은 성인 동행인 1명을 기준으로 접수합니다. 동행인의 사진 촬영이나 녹음은 별도 허가가 필요합니다. 검사 및 시술 공간 출입은 담당자의 안내를 따릅니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_COMPANION
source_origin: authored_synthetic
status: synthetic_draft

## schedule-change

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 항공편이 바뀌어서 방문 날짜를 변경하고 싶어요.
답변: 엘린담 성형외과의원 안내: 새로운 날짜가 필요하면 앱 상담 채팅에 기존 예약과 변경 사유를 남겨 주세요. 이용 가능한 시간은 업무 조회로 확인하고, 병원이 안내한 예약 변경 절차를 진행합니다. 동일 의료진 배정은 별도 확인 사항입니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_SCHEDULE_CHANGE
source_origin: authored_synthetic
status: synthetic_draft

## records

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 상담 내용이나 진료 자료를 귀국 전에 받을 수 있나요?
답변: 엘린담 성형외과의원 안내: 자료 발급은 방문 당일 접수대 또는 앱 상담 채팅에서 신청합니다. 문서 종류에 따라 준비 기간이 다르므로 귀국 일정을 함께 전달해 주세요. 본인 확인과 비용 안내를 받은 후 수령 절차를 진행합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_RECORDS
source_origin: authored_synthetic
status: synthetic_draft

## followup-abroad

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 귀국한 뒤에도 병원에 문의할 수 있나요?
답변: 엘린담 성형외과의원 안내: 귀국 이후에는 앱 상담 채팅에 예약 정보와 질문을 남겨 주세요. 필요한 사진은 담당자가 요청한 경우에 전달합니다. 답변은 후속 상담 절차 안내이며 채팅으로 진단을 확정하지 않습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_FOLLOWUP_ABROAD
source_origin: authored_synthetic
status: synthetic_draft

## photos

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 상담할 사진을 미리 보내거나 상담 내용을 촬영해도 되나요?
답변: 엘린담 성형외과의원 안내: 사전 사진은 담당자가 요청한 자료만 전달합니다. 다른 사람의 얼굴이나 개인정보가 보이는 사진은 보내지 마세요. 상담실 촬영과 녹음은 시작 전에 의료진과 동석자의 허가를 받아야 합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_PHOTOS
source_origin: authored_synthetic
status: synthetic_draft

## accessibility

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 휠체어나 보행 보조기를 사용하면 방문 전에 무엇을 알려야 하나요?
답변: 엘린담 성형외과의원 안내: 방문 전 앱 상담 채팅에 보조기기 종류와 이동 시 필요한 도움을 알려 주세요. 예약 시각에 맞춰 접수 동선을 안내하며 실제 접근 가능 여부는 시설 확인 후 답변합니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_ACCESSIBILITY
source_origin: authored_synthetic
status: synthetic_draft

## cancellation-terms

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 예약을 취소하면 예약금은 얼마나 돌려받나요?
답변: 엘린담 성형외과의원 안내: 이 FAQ에는 예약금 금액과 취소 시점별 환불 기준이 등록되어 있지 않습니다. 결제 전 앱 상담 채팅으로 예약금 유무와 환불 조건을 서면으로 요청해 주세요. 앱의 예약 취소와 결제 금액 환불 처리는 같은 절차로 단정할 수 없습니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_CANCELLATION_TERMS
source_origin: authored_synthetic
status: information_gap

## after-hours

병원: 엘린담 성형외과의원 (hospital_id=33)
질문: 병원 운영 시간이 아닐 때 채팅을 보내면 바로 답해 주나요?
답변: 엘린담 성형외과의원 안내: 휴무일에도 문의 내용을 남길 수 있으나 답변은 병원 운영 시간에 진행합니다. 변경할 예약이 임박했다면 해당 사실을 메시지에 적어 주세요. 읽음 표시만으로 예약 변경이나 의료진 검토가 완료된 것은 아닙니다.

가상 목업 (is_synthetic: true). 근거: SAMPLE_POLICY_033_AFTER_HOURS
source_origin: authored_synthetic
status: synthetic_draft
