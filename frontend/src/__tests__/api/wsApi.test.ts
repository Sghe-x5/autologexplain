import { describe, it, expect, beforeEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { wsApi } from "@/api/wsApi";

// простой мок для WebSocket
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
  closeCalled = false;
  close() {
    this.closeCalled = true;
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

describe("wsApi (unit behavior)", () => {
  let store: ReturnType<typeof createStore>;
  const args = { url: "ws://unit/test" };

  beforeEach(() => {
    store = createStore();
    MockWebSocket.instances.clear();
    vi.clearAllMocks();
  });

  it("initial state is connected=false, ws=null", async () => {
    store.dispatch(wsApi.endpoints.createWebSocket.initiate(args));
    await new Promise((r) => setTimeout(r, 0));

    const data = wsApi.endpoints.createWebSocket.select(args)(
      store.getState()
    ).data;
    expect(data).toEqual({ connected: false, ws: null });
  });

  it("sets connected=true and calls onOpen on open", async () => {
    const onOpen = vi.fn();
    const fullArgs = { ...args, onOpen };
    store.dispatch(wsApi.endpoints.createWebSocket.initiate(fullArgs));
    await new Promise((r) => setTimeout(r, 0));

    const ws = MockWebSocket.instances.get(args.url)!;
    ws.emitOpen();
    await new Promise((r) => setTimeout(r, 0));

    const data = wsApi.endpoints.createWebSocket.select(fullArgs)(
      store.getState()
    ).data;
    expect(data?.connected).toBe(true);
    expect(onOpen).toHaveBeenCalled();
  });

  it("calls onMessage with parsed JSON", async () => {
    const onMessage = vi.fn();
    const fullArgs = { ...args, onMessage };
    store.dispatch(wsApi.endpoints.createWebSocket.initiate(fullArgs));
    await new Promise((r) => setTimeout(r, 0));

    const ws = MockWebSocket.instances.get(args.url)!;
    ws.emitMessage({ foo: 123 });
    expect(onMessage).toHaveBeenCalledWith({ foo: 123 });
  });

  it("sets connected=false and calls onClose on close", async () => {
    const onClose = vi.fn();
    const fullArgs = { ...args, onClose };
    store.dispatch(wsApi.endpoints.createWebSocket.initiate(fullArgs));
    await new Promise((r) => setTimeout(r, 0));

    const ws = MockWebSocket.instances.get(args.url)!;
    ws.emitOpen(); // чтобы было true
    ws.close();
    await new Promise((r) => setTimeout(r, 0));

    const data = wsApi.endpoints.createWebSocket.select(fullArgs)(
      store.getState()
    ).data;
    expect(data?.connected).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });
});
