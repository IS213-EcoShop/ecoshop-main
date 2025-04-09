FROM python:3-slim
WORKDIR /usr/src/app
COPY ./wallet/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./wallet/app.py ./
COPY ./wallet/wallet_utils.py ./
COPY ./utils ./utils
EXPOSE 5402
CMD [ "python", "./app.py" ]
