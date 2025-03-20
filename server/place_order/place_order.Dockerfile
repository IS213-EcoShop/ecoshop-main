FROM python:3-slim
WORKDIR /usr/src/app
COPY ./place_order/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./place_order/place_order.py ./
COPY ./utils ./utils
EXPOSE 5200
CMD [ "python", "./place_order.py" ]
