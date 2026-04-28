import { describe, it, expect, beforeEach, type Mock } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { chatManagementApi } from "@/api/chatManagementApi";

function createStore() {
  return configureStore({
    reducer: { [chatManagementApi.reducerPath]: chatManagementApi.reducer },
    middleware: (gDM) => gDM().concat(chatManagementApi.middleware),
  });
}

describe("chatManagementApi (unit behavior)", () => {
  let store: ReturnType<typeof createStore>;
  const fetchMock = global.fetch as unknown as Mock;

  beforeEach(() => {
    store = createStore();
    fetchMock.mockReset();
    fetchMock.mockImplementation((_url, _options) =>
      Promise.resolve(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
  });

  it("newChat sends POST /chats/new and stores response", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(
        new Response(JSON.stringify({ chat_id: "c1", token: "t1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    const res = await store
      .dispatch(chatManagementApi.endpoints.newChat.initiate(undefined))
      .unwrap();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/chats/new");
    expect(init.method).toBe("POST");

    expect(res).toEqual({ chat_id: "c1", token: "t1" });
  });

  it("renewToken sends POST /chats/renew with body { chat_id }", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(
        new Response(JSON.stringify({ token: "new-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    const res = await store
      .dispatch(
        chatManagementApi.endpoints.renewToken.initiate({ chatId: "abc" })
      )
      .unwrap();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/chats/renew");
    expect(init.method).toBe("POST");

    expect(init.body).toBe(JSON.stringify({ chat_id: "abc" }));

    expect(res).toEqual({ token: "new-token" });
  });
});
