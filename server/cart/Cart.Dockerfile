FROM python:3-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./cart.py ./invokes.py ./
ENV PRODUCT_API_URL="https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{}/"
EXPOSE 5201
CMD ["python", "./cart.py"]
