<script setup lang="ts">
// 디자인 확정 전 화면 자리표시. 디자인이 오면 각 view 에서 이 컴포넌트를 지우고 실제 마크업으로 교체
defineProps<{ id: string; title: string }>()
</script>

<template>
  <section>
    <h1>{{ id }} · {{ title }}</h1>
    <slot />
  </section>
</template>
