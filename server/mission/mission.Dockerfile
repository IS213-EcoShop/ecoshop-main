FROM python:3-slim
WORKDIR /usr/src/app
COPY ./mission/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY ./mission/mission.py ./
COPY ./utils ./utils
EXPOSE 5401
CMD ["python", "./mission.py"]
