FROM python:3-slim
WORKDIR /usr/src/app
COPY ./intermediary/requirements.txt ./
COPY ./utils ./utils
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./intermediary/intermediary.py ./
EXPOSE 5203
CMD ["python", "./intermediary.py"]
