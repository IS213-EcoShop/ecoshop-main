FROM python:3-slim
WORKDIR /usr/src/app
COPY ./delivery/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./delivery/delivery.py ./
COPY ./utils ./utils
EXPOSE 5201
CMD ["python", "./delivery.py"]
