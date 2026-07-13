FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the skill extractor model DIRECTLY from its wheel file
# This automatically handles the correct spaCy version and dependencies
RUN pip install https://huggingface.co/amjad-awad/skill-extractor/resolve/main/skill-extractor-any-py3-none-any.whl

COPY *.py .

CMD ["python", "collector.py"]