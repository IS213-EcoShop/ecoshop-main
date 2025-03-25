FROM python:3-slim
WORKDIR /usr/src/app
COPY ./cart_product/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./cart_product/cart_product.py ./
COPY ./utils ./utils
EXPOSE 5300
CMD ["python", "./cart_product.py"]
