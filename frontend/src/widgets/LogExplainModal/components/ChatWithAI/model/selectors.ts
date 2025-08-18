import type { ChatItem } from "@/lib/chat.schemas";

export const selectNormalizedMessages = (items: ChatItem[]) =>
  items.map((m) => ({
    ...m,
    text: m.text
      .replace(/^```json\n/, "")
      .replace(/\n```$/, "")
      .replace(/Запрос: .*/, ""),
  }));

export const selectUnreadMessages = (
  items: ChatItem[],
  lastReadId: string | null
) => {
  if (!lastReadId) return items;
  const idx = items.findIndex((m) => m.id === lastReadId);
  return idx === -1 ? items : items.slice(idx + 1);
};

export const selectPinnedMessages = (items: ChatItem[]) =>
  items.filter((m: any) => m.pinned === true);
