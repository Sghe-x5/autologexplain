import { wsRegistry } from "@/lib/model/wsRegistry";

export const initStream = (fullUrl: string, chatId: string) => {
  const ws = new WebSocket(fullUrl);
  wsRegistry.set(chatId, ws);
  return ws;
};

export const sendAnalysisStart = (
  chatId: string,
  payload: { filters: unknown; prompt: string }
) => {
  const ws = wsRegistry.get(chatId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        type: "analysis_start",
        request_id: crypto.randomUUID(),
        ...payload,
      })
    );
    return true;
  }
  return false;
};

export const close = (chatId: string) => {
  const ws = wsRegistry.get(chatId);
  if (ws) {
    ws.close();
    wsRegistry.del(chatId);
  }
};

export const closeAll = () => wsRegistry.clear();
