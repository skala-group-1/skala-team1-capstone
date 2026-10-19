<script setup lang="ts">
// 403 "권한 없음" (11 문서 5장). 권한 판단은 backend 가 하고 FE 는 표시만
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <section>
    <h1>403</h1>
    <p>{{ t('error.forbidden') }}</p>
  </section>
</template>
