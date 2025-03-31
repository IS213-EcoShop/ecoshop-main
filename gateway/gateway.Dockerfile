FROM python:3-slim

WORKDIR /usr/src/app

# Copy the requirements file first, install dependencies
COPY ./gateway/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./gateway/server.py ./
COPY ./gateway/resolvers.py ./
COPY ./gateway/graphql_types.py ./

# Expose the application port
EXPOSE 8000

# Set the command to run the application using Uvicorn (FastAPI)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
