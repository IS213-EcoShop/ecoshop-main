FROM python:3.9-slim
WORKDIR /usr/src/app
COPY ../requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY profile/profile.py /usr/src/app/
COPY ../utils /usr/src/app/utils
EXPOSE 5000
ENV FLASK_APP=profile.py
CMD ["python", "profile.py"]
