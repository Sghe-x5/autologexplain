import { describe, it, expect, beforeEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { wsApi } from "@/api/wsApi";

// мок WebSocket
class MockWebSocket {
  static instances = new Map<string, MockWebSocket>();
  url: string;
  listeners: Record<string, Function[]> = { open: [], message: [], close: [] };

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.set(url, this);
  }

  addEventListener(type: "open" | "message" | "close", cb: Function) {
    this.listeners[type].push(cb);
  }

  close() {
    this.listeners["close"].forEach((cb) => cb({}));
  }

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
    reducer: { [wsApi.reducerPath]: wsApi.reducer },
    middleware: (gDM) =>
      gDM({ serializableCheck: false }).concat(wsApi.middleware),
  });
}

describe("wsApi integration", () => {
  let store: ReturnType<typeof createStore>;

  beforeEach(() => {
    store = createStore();
    MockWebSocket.instances.clear();
  });

  it("connects, triggers callbacks and closes", async () => {
    const onOpen = vi.fn();
    const onMessage = vi.fn();
    const onClose = vi.fn();

    const args = { url: "ws://int/test", onOpen, onMessage, onClose };

    store.dispatch(wsApi.endpoints.createWebSocket.initiate(args));
    await new Promise((r) => setTimeout(r, 0));

    const ws = MockWebSocket.instances.get("ws://int/test")!;
    expect(ws).toBeDefined();

    // open
    ws.emitOpen();
    await new Promise((r) => setTimeout(r, 0));
    let data = wsApi.endpoints.createWebSocket.select(args)(
      store.getState()
    ).data;
    expect(data?.connected).toBe(true);
    expect(onOpen).toHaveBeenCalled();

    // message
    ws.emitMessage({ foo: "bar" });
    expect(onMessage).toHaveBeenCalledWith({ foo: "bar" });

    // close
    ws.close();
    await new Promise((r) => setTimeout(r, 0));
    data = wsApi.endpoints.createWebSocket.select(args)(store.getState()).data;
    expect(data?.connected).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });
});
