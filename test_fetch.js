import { apiPostFetch } from "file:///Users/ltn/.openclaw/npm/node_modules/@tencent-weixin/openclaw-weixin/dist/src/api/api.js";

async function test() {
  try {
    const res = await apiPostFetch({
      baseUrl: "https://ilinkai.weixin.qq.com",
      endpoint: "ilink/bot/get_bot_qrcode?bot_type=3",
      body: JSON.stringify({ local_token_list: [] }),
      label: "fetchQRCode",
    });
    console.log("Success:", res);
  } catch (e) {
    console.error("Error:", e);
    console.error("Stack:", e.stack);
    if (e.cause) console.error("Cause:", e.cause);
  }
}
test();
