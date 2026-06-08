FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    texlive-latex-base texlive-latex-extra texlive-latex-recommended \
    texlive-fonts-recommended texlive-fonts-extra \
    texlive-pictures && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ["Latex_from_Json Engine/", "Latex_from_Json Engine/"]
COPY resume_tailor_project/ resume_tailor_project/
COPY demo/ demo/

RUN pip install --no-cache-dir \
    flask flask-cors flask-limiter openai python-dotenv pypdf gunicorn

ENV PORT=10000
ENV ALLOWED_ORIGINS=*
ENV MAX_JD_LENGTH=15000

WORKDIR /app/resume_tailor_project/python_backend

EXPOSE 10000

CMD gunicorn -w 2 -b "0.0.0.0:${PORT}" --timeout 120 server:app