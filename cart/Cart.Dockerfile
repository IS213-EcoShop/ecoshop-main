FROM python:3-slim
WORKDIR /usr/src/app
COPY ./cart/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./cart/cart.py ./
COPY ./utils ./utils
EXPOSE 5201
CMD ["python", "./cart.py"]
