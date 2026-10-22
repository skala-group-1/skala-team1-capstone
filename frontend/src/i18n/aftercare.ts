// 사후관리 화면 문구 (i18n/index.ts 에서 locale 메시지에 합친다 → t('aftercare.*'))
export const aftercareMessages = {
  en: {
    aftercare: {
      title: 'Aftercare',
      body: 'Get aftercare guidance for this procedure and ask questions about your recovery in a separate chat.',
      open: 'Open aftercare chat',
      openFailed: 'Could not open the aftercare chat. Please try again.',
      badge: 'Aftercare',
      section: 'Aftercare {n}',
      day: 'Day {n} after procedure',
      dayZero: 'Procedure day',
      before: 'Before procedure',
      notice: 'General information only. Follow your clinic’s instructions first.',
    },
  },
  ko: {
    aftercare: {
      title: '시술 사후관리',
      body: '이 시술의 사후관리 안내를 받고, 회복 중 궁금한 점을 별도 채팅에서 물어볼 수 있어요.',
      open: '사후관리 채팅 열기',
      openFailed: '사후관리 채팅을 열지 못했어요. 다시 시도해 주세요.',
      badge: '사후관리',
      section: '사후관리 {n}',
      day: '시술 후 {n}일째',
      dayZero: '시술 당일',
      before: '시술 전',
      notice: '일반 정보예요. 병원 안내를 먼저 따라 주세요.',
    },
  },
  zh: {
    aftercare: {
      title: '术后护理',
      body: '在单独的聊天中获取该项目的术后护理指南，并咨询恢复期间的问题。',
      open: '打开术后护理聊天',
      openFailed: '无法打开术后护理聊天，请重试。',
      badge: '术后护理',
      section: '术后护理 {n}',
      day: '术后第{n}天',
      dayZero: '手术当天',
      before: '术前',
      notice: '仅为一般信息，请优先遵循医院的指示。',
    },
  },
  ja: {
    aftercare: {
      title: 'アフターケア',
      body: 'この施術のアフターケア案内を受け取り、回復中の疑問を別のチャットで質問できます。',
      open: 'アフターケアチャットを開く',
      openFailed: 'アフターケアチャットを開けませんでした。もう一度お試しください。',
      badge: 'アフターケア',
      section: 'アフターケア {n}',
      day: '施術後{n}日目',
      dayZero: '施術当日',
      before: '施術前',
      notice: '一般的な情報です。病院の指示を優先してください。',
    },
  },
}
