# main.py
from core.agent import create_log_agent
from core.db.database import get_clickhouse_client

def main():
    try:
        print("Проверка соединения с ClickHouse...")
        get_clickhouse_client() # Проверяем, что можем подключиться при старте
        print("Соединение с ClickHouse успешно установлено.")
    except Exception as e:
        print(f"Не удалось запустить агента. Проверьте данные для подключения к ClickHouse в .env файле.")
        return
        
    agent_executor = create_log_agent()
    
    print("\n--- AI Агент LogSentry (ClickHouse Edition) готов к работе ---")
    print("Модель: Kimi K2. База: ClickHouse.")
    print("Задайте ваш вопрос или напишите 'exit' для выхода.")
    
    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() == 'exit':
                print("LogSentry завершает работу.")
                break
            
            response = agent_executor.invoke({"input": user_input})
            print(f"\nLogSentry: {response['output']}")
        except Exception as e:
            print(f"\nПроизошла критическая ошибка во время выполнения запроса: {e}")

if __name__ == "__main__":
    main()