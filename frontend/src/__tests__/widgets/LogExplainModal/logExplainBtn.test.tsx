import { render, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import showModalReducer from "@/widgets/LogExplainModal/model/showModalSlice";
import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import { describe, it, expect } from "vitest";

const getByTestIdAttr = (id: string) => document.querySelector(`[data-test-id="${id}"]`);

describe("LogExplainBtn", () => {
  const setup = (isShown = false) => {
    const store = configureStore({
      reducer: { showModal: showModalReducer },
      preloadedState: { showModal: { isShown } },
    });

    return render(
      <Provider store={store}>
        <LogExplainBtn />
      </Provider>
    );
  };

  it("должен отобразить кнопку, если модалка скрыта", () => {
    setup(false);
    expect(getByTestIdAttr("open-modal-button")).not.toBeNull();
  });

  it("не должен отображать кнопку, если модалка уже открыта", () => {
    setup(true);
    expect(getByTestIdAttr("open-modal-button")).toBeNull();
  });

  it("при клике должен диспатчить open()", () => {
    const store = configureStore({
      reducer: { showModal: showModalReducer },
      preloadedState: { showModal: { isShown: false } },
    });

    render(
      <Provider store={store}>
        <LogExplainBtn />
      </Provider>
    );

    const btn = getByTestIdAttr("open-modal-button");
    btn && fireEvent.click(btn);
    expect(store.getState().showModal.isShown).toBe(true);
  });
});
