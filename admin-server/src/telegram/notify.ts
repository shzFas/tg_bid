import axios from "axios";

const BOT_TOKEN = process.env.SPEC_BOT_TOKEN;

const CHANNELS: Record<string, string> = {
  ACCOUNTING: process.env.CHANNEL_ACCOUNTING_ID!,
  LAW: process.env.CHANNEL_LAW_ID!,
  EGOV: process.env.CHANNEL_EGOV_ID!,
};

export async function sendApproveTelegram(spec: any) {
  // tg_id — есть в базе?
  if (!spec.tg_id) return;

  let text = `🎉 <b>Вы были одобрены как специалист!</b>\n\n`;

  text += `🧑‍💼 <b>Ваши специализации:</b>\n`;
  for (const s of spec.specializations) {
    text += `• ${s}\n`;
  }

  text += `\n📢 <b>Каналы с заявками:</b>\n`;
  for (const s of spec.specializations) {
    if (CHANNELS[s]) {
      text += `👉 <a href="https://t.me/c/${CHANNELS[s].replace("-100", "")}">Канал: ${s}</a>\n`;
    }
  }

  text += `\nВы теперь можете использовать команду: /my_requests`;

  await axios.post(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    chat_id: spec.tg_id,
    text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
  });
}
