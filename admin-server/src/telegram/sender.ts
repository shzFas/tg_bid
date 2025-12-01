import axios from "axios";

export async function publishToTelegram(req: any) {
  const token = process.env.REQUEST_BOT_TOKEN;
  const channelId = process.env[`CHANNEL_${req.specialization}_ID`];

  const text = `
<b>${mapSpecName(req.specialization)}</b>

✉ <b>Новая заявка (ID: ${req.id}) "админ панель"</b>

👤 <b>Имя:</b> ${req.name}
🏙 <b>Город:</b> ${req.city}
📝 <b>Описание:</b> ${req.description}
  `.trim();

  const keyboard = {
    inline_keyboard: [
      [
        {
          text: "⚒ Взять в работу",
          callback_data: `claim:${req.id}`
        }
      ]
    ]
  };

  const response = await axios.post(
    `https://api.telegram.org/bot${token}/sendMessage`,
    {
      chat_id: channelId,
      text,
      parse_mode: "HTML",
      reply_markup: keyboard
    }
  );

  return {
    message_id: response.data.result.message_id,
    chat_id: channelId,
  };
}

function mapSpecName(spec: string) {
  return spec === "ACCOUNTING" ? "Бухгалтера"
       : spec === "LAW"        ? "Адвоката"
       : spec === "EGOV"       ? "EGOV"
       : "Специалиста";
}
