import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { chatMessagesApi } from "@/api/chatMessagesApi";
import { wsRegistry } from "@/lib/model/wsRegistry";
import { describe, it, expect, beforeEach, vi } from "vitest";

class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  sent: string[] = [];

  send(msg: string) {
    this.sent.push(msg);
  }

  close() {
    this.readyState = 0;
  }
}
(globalThis as any).WebSocket = MockWebSocket;

(globalThis as any).WebSocket = MockWebSocket;

vi.stubGlobal("crypto", {
  randomUUID: () => "uuid-123",
});

describe("chatMessagesApi (integration)", () => {
  let store: ReturnType<typeof makeStore>;

  function makeStore() {
    return configureStore({
      reducer: {
        [chatMessagesApi.reducerPath]: chatMessagesApi.reducer,
      },
      middleware: (gDM) => gDM().concat(chatMessagesApi.middleware),
    });
  }

  beforeEach(() => {
    global.fetch = vi.fn();
    wsRegistry.clear();
    store = makeStore();
    setupListeners(store.dispatch);
  });

  it("analysisStart → отправляет сообщение в WebSocket", async () => {
    const ws = new MockWebSocket();
    wsRegistry.set("c1", ws as any);

    const res = await store
      .dispatch(
        chatMessagesApi.endpoints.analysisStart.initiate({
          chatId: "c1",
          payload: {
            filters: {
              start_date: "2024-01-01",
              end_date: "2024-02-01",
              service: "svc",
            },
            prompt: "test prompt",
          },
        })
      )
      .unwrap();

    expect(res).toEqual({ enqueued: true, request_id: "uuid-123" });
    expect(ws.sent.length).toBe(1);
    expect(JSON.parse(ws.sent[0])).toMatchObject({
      type: "analysis_start",
      prompt: "test prompt",
    });
  });

  it("analysisStart → ошибка если WebSocket закрыт", async () => {
    const ws = new MockWebSocket();
    ws.readyState = 0;
    wsRegistry.set("c2", ws as any);

    await expect(
      store
        .dispatch(
          chatMessagesApi.endpoints.analysisStart.initiate({
            chatId: "c2",
            payload: {
              filters: { start_date: "x", end_date: "y", service: "s" },
              prompt: "zzz",
            },
          })
        )
        .unwrap()
    ).rejects.toEqual({
      status: "CUSTOM_ERROR",
      error: "WebSocket connection closed",
    });
  });

  it("chatTurn → отправляет сообщение в WebSocket", async () => {
    const ws = new MockWebSocket();
    wsRegistry.set("c3", ws as any);

    const res = await store
      .dispatch(
        chatMessagesApi.endpoints.chatTurn.initiate({
          chatId: "c3",
          content: "hello",
        })
      )
      .unwrap();

    expect(res).toEqual({ enqueued: true, request_id: "uuid-123" });
    expect(JSON.parse(ws.sent[0])).toMatchObject({
      type: "chat_turn",
      content: "hello",
    });
  });

  it("autoAnalysis → успешный POST /chats/new", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ chat_id: "c-new", token: "tok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const res = await store
      .dispatch(chatMessagesApi.endpoints.autoAnalysis.initiate())
      .unwrap();

    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/chats/new");
    expect(init.method).toBe("POST");

    expect(res).toEqual({
      chatId: "c-new",
      token: "tok",
      request_id: "uuid-123",
    });
  });

  it("autoAnalysis → ошибка при неуспешном POST", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response("internal error", { status: 500 })
    );

    await expect(
      store.dispatch(chatMessagesApi.endpoints.autoAnalysis.initiate()).unwrap()
    ).rejects.toThrow(/Failed to create chat: 500 internal error/);
  });
});
