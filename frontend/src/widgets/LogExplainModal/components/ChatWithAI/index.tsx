import { ChatWithAIUI } from "./ui/ChatWithAIUI";
import { useChatWithAI } from "./model/useChatWithAI";

export function ChatWithAI({
  autoAnalysisParams,
}: {
  autoAnalysisParams?: {
    filters: {
      start_date: string;
      end_date: string;
      service: string;
      product?: string;
      environment?: string;
    };
    prompt: string;
  };
}) {
  const {
    messages,
    input,
    isAssistantTyping,
    isSending,
    setInput,
    sendMessage,
  } = useChatWithAI({ autoAnalysisParams });

  return (
    <ChatWithAIUI
      messages={messages}
      input={input}
      isAssistantTyping={isAssistantTyping}
      isSending={isSending}
      onInputChange={setInput}
      onSend={sendMessage}
    />
  );
}
