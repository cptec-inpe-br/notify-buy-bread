from pydantic import BaseModel
from typing import Optional

class CoffeeReminderRequest(BaseModel):
    """
    Modelo para a requisição de lembrete de café.
    
    Atributos:
        subject: Assunto do e-mail (opcional, padrão: "Tá na hora do cafezinho")
        message: Mensagem personalizada (opcional, será adicionada antes da mensagem padrão)
    """
    subject: str = "Tá na hora do cafezinho"
    message: Optional[str] = None
