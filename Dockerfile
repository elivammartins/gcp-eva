FROM python:3.11-slim
ENV PYTHONUNBUFFERED True
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
CMD exec functions-framework --target=process_data --port=$PORT
