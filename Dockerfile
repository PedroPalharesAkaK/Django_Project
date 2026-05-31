# Usa uma versão oficial e leve do Python
FROM python:3.12-slim

# Impede o Python de gravar arquivos .pyc e força a saída no terminal sem atrasos
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências e instala
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o resto do código do projeto para dentro do container
COPY . /app/