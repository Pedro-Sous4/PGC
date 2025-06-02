# Base
FROM python:3.12-slim

# Diretório de trabalho
WORKDIR /app

# Copia arquivos
COPY . /app/

# Instala dependências
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Porta que o Django vai expor
EXPOSE 8000

# Comando padrão
CMD ["python", "manage.py", "runserver", "192.168.1.105:8000"]
