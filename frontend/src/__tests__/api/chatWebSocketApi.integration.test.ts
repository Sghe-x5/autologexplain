import { describe, it, expect, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { chatWebSocketApi } from "@/api/chatWebSocketApi";

// Простой мок WebSocket для интеграции
class MockWebSocket {
  static instances = new Map<string, MockWebSocket>();
  url: string;
  listeners: Record<string, Function[]> = { open: [], message: [], close: [] };

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.set(url, this);
  }
  addEventListener(type: string, cb: Function) {
    this.listeners[type].push(cb);
  }
  close() {
    this.listeners["close"].forEach((cb) => cb({}));
  }

  // вспомогательные методы для тестов
  emitOpen() {
    this.listeners["open"].forEach((cb) => cb({}));
  }
  emitMessage(msg: any) {
    this.listeners["message"].forEach((cb) =>
      cb({ data: JSON.stringify(msg) })
    );
  }
}

(globalThis as any).WebSocket = MockWebSocket as any;

function createStore() {
  return configureStore({
    reducer: { [chatWebSocketApi.reducerPath]: chatWebSocketApi.reducer },
    middleware: (gDM) => gDM().concat(chatWebSocketApi.middleware),
  });
}

describe("chatWebSocketApi integration", () => {
  let store: ReturnType<typeof createStore>;

  beforeEach(() => {
    store = createStore();
    MockWebSocket.instances.clear();
  });

  it("full cycle: open → message → close", async () => {
    const args = { chatId: "int-1", token: "tok", wsUrl: "ws://int/" };

    // запускаем стрим
    store.dispatch(chatWebSocketApi.endpoints.streamChat.initiate(args));
    await new Promise((r) => setTimeout(r, 0));

    const expectedUrl = "ws://int/ws/chats/int-1?token=tok";
    const ws = MockWebSocket.instances.get(expectedUrl)!;

    // open
    ws.emitOpen();
    await new Promise((r) => setTimeout(r, 0));
    let data = chatWebSocketApi.endpoints.streamChat.select(args)(
      store.getState()
    ).data;
    expect(data?.connected).toBe(true);

    // message
    ws.emitMessage({
      type: "final",
      message_id: "m1",
      request_id: "r1",
      content: "hello",
    });
    await new Promise((r) => setTimeout(r, 0));
    data = chatWebSocketApi.endpoints.streamChat.select(args)(
      store.getState()
    ).data;
    expect(data?.items).toHaveLength(1);
    expect(data?.items?.[0].text).toBe("hello");

    // close
    ws.close();
    await new Promise((r) => setTimeout(r, 0));
    data = chatWebSocketApi.endpoints.streamChat.select(args)(
      store.getState()
    ).data;
    expect(data?.connected).toBe(false);
  });
});
