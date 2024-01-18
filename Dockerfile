FROM python:3.11

RUN apt-get update

# Clone repository
COPY . /app
WORKDIR /app

RUN apt-get install -y libglib2.0-0 libgl1-mesa-glx && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN python -m pip install -r requirements.txt

CMD ["uvicorn", "server.server:app", "--host", "0.0.0.0" , "--port", "8000"]
