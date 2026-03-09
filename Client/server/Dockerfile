FROM python:3.12-slim

WORKDIR /app

COPY server.py /app/server.py

ENV PORT=8080
ENV GUARDIANSTAR_STATE_FILE=/data/server_state.json

EXPOSE 8080

CMD ["python", "server.py"]
