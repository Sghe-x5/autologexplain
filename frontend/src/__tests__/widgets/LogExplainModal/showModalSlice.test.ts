import { describe, expect, it } from "vitest";
import showModal, {
  close,
  open,
} from "../../../widgets/LogExplainModal/model/showModalSlice";

describe("showModalSlice", () => {
  it("should handle initial state", () => {
    expect(showModal(undefined, { type: "unknown" })).toEqual({
      isShown: false,
    });
  });

  it("should handle open action", () => {
    const initialState = { isShown: false };
    const newState = showModal(initialState, open());
    expect(newState.isShown).toBe(true);
  });

  it("should handle close action", () => {
    const initialState = { isShown: true };
    const newState = showModal(initialState, close());
    expect(newState.isShown).toBe(false);
  });
});
