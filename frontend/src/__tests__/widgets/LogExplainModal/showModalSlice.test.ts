import { describe, expect, it } from "vitest";
import showModal, {
  close,
  open,
} from "../../../widgets/LogExplainModal/model/showModalSlice";

describe("showModalSlice", () => {
  it("проверка инициализации", () => {
    expect(showModal(undefined, { type: "unknown" })).toEqual({
      isShown: false,
    });
  });

  it("проверка открытия окна", () => {
    const initialState = { isShown: false };
    const newState = showModal(initialState, open());
    expect(newState.isShown).toBe(true);
  });

  it("проверка закрытия окна", () => {
    const initialState = { isShown: true };
    const newState = showModal(initialState, close());
    expect(newState.isShown).toBe(false);
  });

  it("не должен изменять состояние при неизвестном действии", () => {
    const prevState = { isShown: false };
    const newState = showModal(prevState, { type: "UNKNOWN_ACTION" });
    expect(newState).toEqual(prevState);
  });

  it("проверка множественного открытия окна", () => {
    const state = { isShown: false };
    const firstOpen = showModal(state, open());
    const secondOpen = showModal(firstOpen, open());
    expect(secondOpen.isShown).toBe(true);
  });

  it("проверка множественного закрытия окна", () => {
    const state = { isShown: true };
    const firstClose = showModal(state, close());
    const secondClose = showModal(firstClose, close());
    expect(secondClose.isShown).toBe(false);
  });

  it("проверка последовательного открытия/закрытия", () => {
    let state = { isShown: false };
    state = showModal(state, open());
    expect(state.isShown).toBe(true);
    state = showModal(state, close());
    expect(state.isShown).toBe(false);
    state = showModal(state, open());
    expect(state.isShown).toBe(true);
  });
});
