<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <section>
    <h1>404</h1>
    <p>{{ t('error.notFound') }}</p>
  </section>
</template>
