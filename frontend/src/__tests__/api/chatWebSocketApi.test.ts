import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type Mock,
} from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import type { ChatData } from "@/lib/chat.schemas";

// ВАЖНО: порядок моков — сначала wsRegistry и WebSocket, потом импортируем тестируемый модуль
vi.mock("@/lib/model/wsRegistry", () => {
  return {
    wsRegistry: {
      set: vi.fn(),
      del: vi.fn(),
    },
  };
});

// Опционально, если модуль где-то тянет WS_BASE — замокаем, чтобы не влиял
vi.mock("@/lib/consts", () => ({
  WS_BASE: "ws://dummy-base",
  baseUrl: "http://dummy-base", // добавить, чтобы не падало
}));

// Примитивный мок WebSocket с реестром инстансов по URL
type Listener = (event: any) => void;
class MockWebSocket {
  static instances = new Map<string, MockWebSocket>();

  url: string;
  readyState = 0;
  private listeners: Record<string, Listener[]> = {
    open: [],
    message: [],
    close: [],
    error: [],
  };

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.set(url, this);
  }

  addEventListener(type: "open" | "message" | "close" | "error", cb: Listener) {
    (this.listeners[type] ||= []).push(cb);
  }
  removeEventListener(
    type: "open" | "message" | "close" | "error",
    cb: Listener
  ) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== cb);
  }

  // Эмиттеры "со стороны" теста
  emitOpen() {
    this.readyState = 1;
    for (const cb of this.listeners.open || []) cb({});
  }
  emitMessage(data: any) {
    for (const cb of this.listeners.message || [])
      cb({ data: typeof data === "string" ? data : JSON.stringify(data) });
  }
  emitClose() {
    this.readyState = 3;
    for (const cb of this.listeners.close || []) cb({});
  }

  // Вызывается RTK при очистке кэша
  close() {
    this.emitClose();
  }
}

// Глобально подменяем WebSocket до импорта модуля
globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket;

// Теперь импортируем тестируемый модуль
import { chatWebSocketApi } from "@/api"; // поправь путь
// Если хуки не нужны в тестах, их можно не импортировать
import { wsRegistry } from "@/lib/model/wsRegistry";

const wsRegistrySet = wsRegistry.set as unknown as Mock;
const wsRegistryDel = wsRegistry.del as unknown as Mock;

describe("chatWebSocketApi (behavior)", () => {
  function createStore() {
    return configureStore({
      reducer: { [chatWebSocketApi.reducerPath]: chatWebSocketApi.reducer },
      middleware: (gDM) => gDM().concat(chatWebSocketApi.middleware),
    });
  }
  type AppStore = ReturnType<typeof createStore>;

  let store: AppStore;

  beforeEach(() => {
    store = createStore();
    wsRegistrySet.mockClear();
    wsRegistryDel.mockClear();
    MockWebSocket.instances.clear();
  });

  afterEach(() => {
    // гарантируем очистку активностей api между тестами
    store.dispatch(chatWebSocketApi.util.resetApiState());
  });

  it("initial state: returns disconnected=false, empty items", async () => {
    const args = { chatId: "c1", token: "t", wsUrl: "ws://host/" };
    await store
      .dispatch(chatWebSocketApi.endpoints.streamChat.initiate(args))
      .unwrap();

    const sel = chatWebSocketApi.endpoints.streamChat.select(args);
    const data = sel(store.getState())?.data as ChatData | undefined;

    expect(data).toBeDefined();
    expect(data?.connected).toBe(false);
    expect(Array.isArray(data?.items)).toBe(true);
    expect(data?.items?.length).toBe(0);
  });

  it("sets connected=true on WebSocket open and registers in wsRegistry", async () => {
    const args = { chatId: "chat-42", token: "tok@", wsUrl: "ws://srv/" };
    await store
      .dispatch(chatWebSocketApi.endpoints.streamChat.initiate(args))
      .unwrap();

    // Проверяем сформированный URL
    const expectedUrl = "ws://srv/ws/chats/chat-42?token=tok%40";
    const ws = MockWebSocket.instances.get(expectedUrl);
    expect(ws).toBeDefined();

    // При создании — set(chatId, ws)
    expect(wsRegistrySet).toHaveBeenCalledTimes(1);
    expect(wsRegistrySet).toHaveBeenCalledWith("chat-42", ws);

    // Эмулируем open
    ws!.emitOpen();

    const sel = chatWebSocketApi.endpoints.streamChat.select(args);
    const data = sel(store.getState())?.data as ChatData;

    expect(data.connected).toBe(true);
  });

  it('appends assistant "final" message with correct shape', async () => {
    const args = { chatId: "cid", token: "tok k", wsUrl: "ws://x" };
    await store
      .dispatch(chatWebSocketApi.endpoints.streamChat.initiate(args))
      .unwrap();

    const expectedUrl = "ws://x/ws/chats/cid?token=tok%20k";
    const ws = MockWebSocket.instances.get(expectedUrl)!;

    ws.emitOpen();
    ws.emitMessage({
      type: "final",
      message_id: "m-1",
      request_id: "r-1",
      content: "Hello",
    });

    const sel = chatWebSocketApi.endpoints.streamChat.select(args);
    const data = sel(store.getState())?.data as ChatData;

    expect(data.items).toHaveLength(1);
    expect(data.items?.[0]).toEqual({
      role: "assistant",
      id: "m-1",
      requestId: "r-1",
      text: "Hello",
      pending: false,
    });
  });

  it("on close: connected=false and wsRegistry.del called", async () => {
    const args = { chatId: "ch", token: "t", wsUrl: "ws://h/" };
    const sub = store.dispatch(
      chatWebSocketApi.endpoints.streamChat.initiate(args)
    );

    const expectedUrl = "ws://h/ws/chats/ch?token=t";
    const ws = MockWebSocket.instances.get(expectedUrl)!;

    ws.emitOpen();

    // Эмулируем серверный close
    ws.emitClose();

    // connected=false после close
    await new Promise((r) => setTimeout(r, 0));
    const sel = chatWebSocketApi.endpoints.streamChat.select(args);
    const dataAfterClose = sel(store.getState())?.data as ChatData;
    expect(dataAfterClose.connected).toBe(false);

    // del вызван хотя бы раз при событии close
    expect(wsRegistryDel).toHaveBeenCalledTimes(1);
    expect(wsRegistryDel).toHaveBeenCalledWith("ch");

    // Теперь отписываемся — RTK вызовет ws.close() и второй del
    sub.unsubscribe();
    expect(wsRegistryDel).toHaveBeenCalledTimes(1);
  });
});
