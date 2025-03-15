FROM python:3.9-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./place_order.py ./invokes.py ./
EXPOSE 5200
CMD [ "python", "./place_order.py" ]
