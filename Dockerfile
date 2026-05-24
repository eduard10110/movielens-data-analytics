FROM python:3.11-slim
LABEL maintainer="team6-movielens-integrated"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 apt-transport-https unixodbc unixodbc-dev gcc g++ \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
        https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
COPY sql/ /sql/
COPY scripts/ /scripts/
CMD ["python", "main.py"]
