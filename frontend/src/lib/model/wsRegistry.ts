const sockets = new Map<string, WebSocket>();
export const wsRegistry = {
  get: (chatId: string) => sockets.get(chatId) ?? null,
  set: (chatId: string, ws: WebSocket) => sockets.set(chatId, ws),
  del: (chatId: string) => sockets.delete(chatId),
  getAllKeys: () => sockets.keys(),
  clear: () => {
    // Закрываем все соединения и очищаем Map
    sockets.forEach((ws) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
    sockets.clear();
  },
};
