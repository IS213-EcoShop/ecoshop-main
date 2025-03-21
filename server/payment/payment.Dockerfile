FROM python:3-slim
WORKDIR /usr/src/app
COPY ./payment/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./payment/payment.py ./
EXPOSE 5202
CMD ["python", "./payment.py"]
