FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py /app/server.py

ENV PORT=8080
ENV GUARDIANSTAR_DATABASE_URL=sqlite:////data/guardianstar.db
ENV GUARDIANSTAR_LEGACY_STATE_FILE=/data/server_state.json

EXPOSE 8080

CMD ["python", "server.py"]
