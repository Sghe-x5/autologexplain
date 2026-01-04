const sockets = new Map<string, WebSocket>();
export const wsRegistry = {
  get: (chatId: string) => sockets.get(chatId) ?? null,
  set: (chatId: string, ws: WebSocket) => sockets.set(chatId, ws),
  del: (chatId: string) => sockets.delete(chatId),
};
