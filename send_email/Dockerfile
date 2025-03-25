FROM python:3.9-slim
WORKDIR /usr/src/app

COPY ./send_email/requirements.txt ./requirements.txt
COPY ./send_email/quickstart.py ./quickstart.py
COPY ./send_email/token.json ./token.json
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

COPY ./send_email/send_email.py .

EXPOSE 5002
ENV FLASK_APP=send_email.py

CMD ["python", "send_email.py"]

