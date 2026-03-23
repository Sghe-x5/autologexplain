import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { chatManagementApi } from "@/api/chatManagementApi";
import { describe, it, expect, beforeEach, vi } from "vitest";

describe("chatManagementApi (integration)", () => {
  let store: ReturnType<typeof makeStore>;

  function makeStore() {
    return configureStore({
      reducer: {
        [chatManagementApi.reducerPath]: chatManagementApi.reducer,
      },
      middleware: (gDM) => gDM().concat(chatManagementApi.middleware),
    });
  }

  beforeEach(() => {
    global.fetch = vi.fn();
    store = makeStore();
    setupListeners(store.dispatch);
  });

  it("newChat → sends POST /chats/new and returns chat_id + token", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ chat_id: "c1", token: "t1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const res = await store
      .dispatch(chatManagementApi.endpoints.newChat.initiate())
      .unwrap();

    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/chats/new");
    expect(init.method).toBe("POST");

    expect(res).toEqual({ chat_id: "c1", token: "t1" });
  });

  it("renewToken → sends POST /chats/renew with body { chat_id } and returns token", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ token: "new-token" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const res = await store
      .dispatch(
        chatManagementApi.endpoints.renewToken.initiate({ chatId: "abc" })
      )
      .unwrap();

    const [url, init] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/chats/renew");
    expect(init.method).toBe("POST");

    expect(init.body).toBe(JSON.stringify({ chat_id: "abc" }));

    expect(res).toEqual({ token: "new-token" });
  });
});
