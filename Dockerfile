# Imagem base oficial do Python
FROM python:3.12-slim

ENV PYTHONPATH=/app
# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de requirements
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY . .

# Expõe a porta padrão do FastAPI (uvicorn)
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["python", "src/main.py"]
