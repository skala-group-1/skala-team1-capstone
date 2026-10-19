<script setup lang="ts">
// 「화면 목록」 C2 회원가입 (고객만, 「인증·인가 설계」)
// TODO(fe): 폼 — 이메일, 비번(8자 이상·영문+숫자), 이름, 생년월일, 성별(F/M/X), 국적(ISO 2자리), 사용언어(en/zh/ja)
// TODO(fe): auth.signup(body) → EMAIL_DUPLICATED(409) / VALIDATION_FAILED(400, details.fields) 필드별 표시
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C2" title="회원가입" />
</template>
