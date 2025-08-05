# Imagem base oficial do Python
FROM python:3.12-slim

ENV PYTHONPATH=/app/src
# Define diretório de trabalho
WORKDIR /app

RUN apt-get update && apt-get install -y supervisor

# Copia arquivos de requirements
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY . .
COPY start.sh /start.sh

# Expõe a porta padrão do FastAPI (uvicorn)
EXPOSE 8000 8080

CMD ["./start.sh"]
