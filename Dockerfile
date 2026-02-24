# Образ с Python и Chromium для Playwright
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py config.json ./

# Папка для сгенерированных карточек (volume или создаётся при запуске)
RUN mkdir -p output

CMD ["python", "main.py"]
