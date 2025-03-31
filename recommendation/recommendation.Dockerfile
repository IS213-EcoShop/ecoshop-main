FROM python:3-slim
WORKDIR /usr/src/app
COPY ./recommendation/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./recommendation/recommendation.py ./
COPY ./utils ./utils
EXPOSE 5204
CMD ["python", "./recommendation.py"]
